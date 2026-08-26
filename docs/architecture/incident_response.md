# Incident Mode / Evidence Readiness

Source: [`backend/incidents/`](../../backend/incidents/), [`backend/evidence/`](../../backend/evidence/), [`backend/api/routers/incidents.py`](../../backend/api/routers/incidents.py), [`apps/dashboard/src/pages/IncidentResponsePage.tsx`](../../apps/dashboard/src/pages/IncidentResponsePage.tsx)
Tests: [`tests/test_incidents.py`](../../tests/test_incidents.py), [`apps/dashboard/src/pages/IncidentResponsePage.test.tsx`](../../apps/dashboard/src/pages/IncidentResponsePage.test.tsx)

## What this is

The PREPARE → RESPOND stages of Sentinel's core loop (`PROJECT_CONTEXT.md`):
it takes an elevated-risk episode the existing model already detected and
connects it through to a reason code, evidence readiness, and a response-
preparation workflow that always ends in "merchant confirmation required."

```
real risk-category event (data/scenarios/events.csv)
    -> real detection by the SAME saved artifact/threshold used by /risk
    -> incident (backend/incidents/incident_service.py)
    -> reason code (backend/evidence/reason_codes.py)
    -> evidence readiness (backend/evidence/evidence_service.py)
    -> priority (transparent, disclosed rules)
    -> response preparation (frontend-only workflow tracker)
```

This is explicitly **not** a real dispute-submission system. It never
fabricates evidence, never claims a dispute was filed, never claims a
dispute would be won, and never claims access to Razorpay's actual dispute
infrastructure. Every claim below is labeled OBSERVED, MODELED, DERIVED, or
SYNTHETIC/PROTOTYPE (`backend/api/schemas/common.py:Provenance`).

## Incident model

An incident is **not** invented from a risk score threshold in isolation —
it is grounded in a real synthetic-benchmark risk episode:

- **Source**: `data/scenarios/events.csv`, filtered to `category == "risk"`
  (the five risk-type scenarios: `chargeback_deterioration`, `refund_shock`,
  `fulfillment_degradation`, `customer_mix_shift`, `compound_risk` — never
  the four `benign_growth` hard-negative types, which are deliberately
  healthy-growth examples, not incidents).
- **Incident ID**: `f"INC-{event_id}"` — a deterministic, reversible mapping
  to the generator's own event_id, not a fabricated identifier.
- **Window**: the event's own `start_date`/`end_date`/`recovery_end_date`/
  `duration_days` — real generator scenario metadata, not invented dates.
- **Status**: `"active"` if the event's `recovery_end_date` is on or after
  the merchant's last observed benchmark date (the episode's designed
  recovery arc had not yet fully closed within the fixed 180-day history),
  else `"resolved"`. Derived, not modeled.

Every other section of an incident — risk, exposure, liquidity — is
produced by calling the **existing** `backend/risk/risk_service.py` and
`backend/risk/explainability_service.py` functions at the incident's
`detected_date` (see below). No new prediction logic, no new SHAP logic,
no new liquidity formula exists anywhere in this module.

## Incident selection logic ("detection")

A risk-category event only becomes a surfaced incident if the **same saved
artifact** used by `/merchants/{id}/risk` crosses its **own existing**
`decision_threshold` on at least one day within `[event.start_date,
event.end_date]`:

```python
for day in range(start_day, end_day + 1):
    X = feature_row(merchant_id, day)
    probability = artifact.calibrated_pipeline.predict_proba(X)[0, 1]
    if probability >= artifact.decision_threshold:
        detected_day = day  # first such day
        break
```

This reuses the exact artifact, exact feature pipeline, and exact
already-validated threshold — no second risk engine, no arbitrary new
number. `detected_date` (the first day inside the window the model actually
flagged) is what every downstream risk/exposure/liquidity/SHAP call uses as
`as_of_date`.

**This is a genuinely selective bar, not a formality**: empirically, 50 of
the 80 risk events in the benchmark (across 34 of 50 merchants) meet it —
consistent with the model's own documented imperfect recall
(`docs/research/baseline_ml_report.md`), not tuned to hit a target count. A
merchant whose risk episodes the model never flagged correctly shows **zero
incidents** — an honest empty state (see `IncidentModeIntro`'s framing),
not a bug. `tests/test_incidents.py::test_incident_selection_rule_matches_documented_detection_bar`
independently recomputes this bar against the real artifact and asserts it
matches the service's own output exactly.

**Prototype assumption, stated explicitly**: evaluating a day-by-day sweep
strictly inside `[start_date, end_date]` (not before or after) was chosen
for simplicity and because it directly answers "did the existing model ever
flag this specific injected episode." It is not a claim about optimal
early-warning timing — `docs/research/baseline_ml_report.md`'s warning
lead-time analysis is the authoritative treatment of that question.

## Reason-code taxonomy

**A SENTINEL SYNTHETIC PROTOTYPE TAXONOMY — not Razorpay's, a card
network's, or any real dispute system's proprietary reason-code
taxonomy.** Every incident/evidence response repeats this disclaimer
verbatim (`backend/evidence/reason_codes.py`).

One reason code per risk `event_type`, a fixed 1:1 mapping:

| event_type | Reason code | Why |
|---|---|---|
| `fulfillment_degradation` | `GOODS_OR_SERVICE_NOT_RECEIVED` | The event's own `affects` are fulfillment on-time rate, delay, and a linked chargeback increase — late/failed delivery driving disputes. |
| `refund_shock` | `CREDIT_NOT_PROCESSED` | A spike in refund rate maps to "customer disputes an unresolved credit." |
| `chargeback_deterioration` | `SUSPECTED_FRAUD_OR_UNAUTHORIZED` | This event type touches ONLY chargeback_rate — the natural catch-all for a chargeback increase with no other observable cause. |
| `customer_mix_shift` | `UNRECOGNIZED_TRANSACTION` | Rising new-customer share + a lagged chargeback increase — unfamiliar first-time purchasers are the plausible analog for "cardholder doesn't recognize this charge." |
| `compound_risk` | `MULTIPLE_FACTORS` | Genuinely multi-causal (bundles refund, chargeback, fulfillment) — not forced into one of the above. |

Every mapping is a **prototype choice**, not a verified real-world
correspondence — it exists so the evidence-readiness engine has a
controlled input, not to claim clinical accuracy about causation.

## Evidence categories and readiness logic

Seven categories, matching `PROJECT_CONTEXT.md`'s list exactly: `invoice`,
`payment_confirmation`, `delivery_proof`, `tracking_information`,
`refund_confirmation`, `customer_communication`, `service_access_records`.
Each reason code requires a fixed subset (`backend/evidence/reason_codes.py:REASON_CODE_REQUIRED_EVIDENCE`).

**Availability is never fabricated.** Every category resolves to
available/missing via one of two kinds of rule
(`backend/evidence/evidence_service.py`), each disclosed in the
response's own `rationale` field:

| Category | Rule | Provenance |
|---|---|---|
| `invoice`, `payment_confirmation` | Always available — a processed transaction inherently has these. | `synthetic_prototype` (an assumption, not verified per transaction) |
| `delivery_proof`, `tracking_information` | Available if the incident window's OBSERVED mean on-time fulfillment rate ≥ 70% (`FULFILLMENT_EVIDENCE_COMPLETENESS_THRESHOLD`, fixed, not tuned per incident). | `derived` |
| `refund_confirmation` | Available if OBSERVED `refund_count` summed over the window is > 0. | `derived` |
| `customer_communication` | Available if `business_tier` is `mid` or `large` (a support-logging-maturity assumption). | `synthetic_prototype` |
| `service_access_records` | Available only for `SaaS`/`Digital Goods` archetypes (a natural-digital-access-log assumption). | `synthetic_prototype` |

**Readiness status** (`evidence_service.readiness_status_from_counts`):
`ready` if all required categories are available, `insufficient` if none
are, else `partial`. Because `invoice` and `payment_confirmation` are
required by every reason code and always available, `available_count` is
always ≥ 2 whenever `required_count` > 0 — so `insufficient` is a real,
tested code path (`test_readiness_status_classification_is_exhaustive_and_correct`)
that does not occur naturally in this particular 50×180 benchmark run. This
is stated here rather than hidden.

**Missing evidence** is sorted by a fixed, disclosed importance order
(`EVIDENCE_PRIORITY_ORDER`: payment confirmation, invoice, delivery proof,
tracking information, refund confirmation, customer communication, service
access records) — the same order for every incident, never reordered to
make a particular case look better or worse.

Nothing here ever generates an actual document, tracking number, invoice
number, or message body — only a category-level yes/no with a disclosed
reason.

## Prioritization

A transparent, rule-based heuristic — **not** a model
(`backend/incidents/incident_service.py:_compute_priority`). Each incident
accumulates plain-English reasons, then:

- **High**: 2 or more reasons apply.
- **Medium**: exactly 1 reason applies.
- **Low**: 0 reasons apply.

The reasons themselves, each independently checkable in the response:

1. Liquidity stress at the detected date ≥ 1.0 (the same anchor the
   dashboard's liquidity gauge uses — exposure would consume all or more of
   available liquidity).
2. Evidence readiness is `insufficient` or `partial`.
3. The model's probability stayed at or above the decision threshold for
   ≥ 50% of the incident's window days (a "sustained," not one-off, signal).
4. Estimated case count ≥ 5 (`HIGH_CASE_COUNT_THRESHOLD`, illustrative and
   fixed, not tuned per incident).

Every incident's response includes `priority_reasons` verbatim, so a
merchant can see exactly why something is marked high priority — never an
opaque score.

## Affected cases — an aggregate count, not fabricated case records

The benchmark contains only **daily aggregate** observations, not
transaction-level dispute records. Rather than inventing individual case
entries (fake order IDs, fake customer names), `case_summary` reports one
honest, derived number: the sum of OBSERVED `chargeback_count` over the
incident's window. `case_summary.note` states this limitation explicitly.
Evidence readiness is therefore modeled at the **incident** (episode)
level, not per individual transaction — a documented simplification, not a
claim that per-case evidence tracking wouldn't matter in a real system.

## Response preparation — merchant confirmation boundary

`ResponsePreparation` (frontend-only, no backend call) renders a fixed
four-step tracker: **Review → Evidence check → Prepare response → Merchant
confirmation required**. "Prepare response" is disabled until evidence
readiness reaches `ready`; clicking it only reveals a local confirmation
message — it does not call any API, does not persist anything, and does
not submit anything externally. The message states plainly: *"Nothing has
been submitted anywhere — this prototype does not file or submit disputes.
A merchant would need to explicitly review and confirm this response
before it could be prepared for submission through Razorpay's actual
dispute process, which Sentinel does not have access to."*

There is intentionally **no** incident/evidence mutation endpoint anywhere
in the backend — `tests/test_incidents.py::test_no_mutating_incident_routes_exist`
asserts every registered incident route is GET-only.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/merchants/{merchant_id}/incidents` | Summary list of this merchant's incidents |
| GET | `/incidents/{incident_id}` | Full incident detail (risk, exposure, liquidity, drivers, reason code, case summary, evidence readiness, scenario context) |
| GET | `/incidents/{incident_id}/evidence` | Just the evidence-readiness section of the same incident |

`incident_id` is global (not nested under a merchant in the URL) — it
reverse-resolves to the originating event and merchant internally
(`backend/incidents/incident_service.py:get_incident`). Unknown
merchant/incident → 404 (`MerchantNotFoundError`/`IncidentNotFoundError`).
No internal filesystem path is ever exposed in a response.

## Frontend

`IncidentResponsePage` (nav item now enabled — the only previously-disabled
item this task turns on) is a master/detail layout: `IncidentList` on the
left, and on the right — deliberately reusing the **exact same** Overview
components (`RiskSummary`, `ExposureCard`, `LiquidityCard`, `RiskDrivers`)
via a thin `IncidentDetail -> RiskResponse` type adapter, not a
reimplementation — followed by incident-specific `IncidentHeader`,
`CaseSummaryCard`, `EvidenceChecklist`, and `ResponsePreparation`. This
literal code reuse is what makes the risk → exposure → liquidity → drivers
→ incident → evidence → preparation chain visibly the same intelligence,
not a parallel, disconnected feature.

Color usage is deliberately restrained: red is reserved for `elevated` risk
state and `insufficient` evidence only; priority uses amber/slate, not a
stoplight of reds, per the explicit "avoid excessive red / fake urgency"
direction.

## Limitations

- **Incident-level, not transaction-level.** See "Affected cases" above.
- **Evidence-availability rules are prototype heuristics** grounded partly
  in observed benchmark signals and partly in explicitly-labeled business
  assumptions (tier, archetype) — not a real evidence-management system
  integration.
- **The reason-code taxonomy is a prototype invention**, not a real card
  network or Razorpay taxonomy.
- **`insufficient` evidence readiness does not occur naturally** in this
  50×180 benchmark run (see "Evidence categories" above) — the code path is
  real and tested, but every actual incident in this benchmark reaches at
  least `partial`.
- **Only the 30-day horizon** has a saved artifact, matching every other
  Sentinel screen's limitation.
- **No persistence.** Every incident is recomputed fresh from the
  startup-loaded benchmark tables on every request — there is no database,
  no stored "an analyst reviewed this" state, consistent with this task's
  explicit instruction not to add a new database.
- **This is a synthetic-benchmark research prototype.** Nothing here is a
  claim about real Razorpay dispute infrastructure, real evidentiary
  standards, or real dispute outcomes.
