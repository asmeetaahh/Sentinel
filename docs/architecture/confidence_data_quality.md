# Confidence / Data Quality V1

Source: [`backend/risk/confidence_service.py`](../../backend/risk/confidence_service.py), [`backend/api/schemas/risk.py`](../../backend/api/schemas/risk.py) (`DataQualitySection`), [`apps/dashboard/src/components/overview/ConfidenceBadge.tsx`](../../apps/dashboard/src/components/overview/ConfidenceBadge.tsx)
Tests: [`tests/test_confidence.py`](../../tests/test_confidence.py), [`apps/dashboard/src/components/overview/ConfidenceBadge.test.tsx`](../../apps/dashboard/src/components/overview/ConfidenceBadge.test.tsx)

## What this is

A deterministic transparency layer over the existing risk assessment —
**not a second model, not a statistical confidence interval, and not a
fabricated percentage.** It answers one question honestly: "how much
should this specific risk read be trusted, given how much of this
merchant's history actually backs it?"

```
existing resolved day_index (backend/services/lookups.resolve_day_index)
    -> history_days = day_index + 1
    -> compared against ml/features/config.py's OWN window constants
       (WINDOW_MEDIUM=28, WINDOW_LONG=60) — never redeclared
existing feature row (state.features, already built by ml.features)
    -> feature_coverage_status: every state.feature_columns value present?
    -> confidence_level: high / medium / limited (fixed, disclosed rules)
    -> exposed as RiskResponse.data_quality, alongside model/exposure/liquidity
```

Nothing here computes a feature, trains anything, or asks the model
anything. Both signals are read directly off state the backend already
built for the risk call itself.

## Why these two signals, and no others

`ml/features`' own primitives use `rolling(window, min_periods=1)` /
`expanding(min_periods=1)` (see `docs/architecture/feature_engineering.md`
"Known limitations"): every feature value is always numerically present,
even when computed on far less data than its nominal window — *"a 60d
feature computed at day_index=2 is really a 3-day average."* That
existing, already-documented limitation is precisely the thing a
confidence signal should surface. `history_days` compared against the
pipeline's own window sizes is the correct, already-true way to surface
it — not a new statistic invented for this task, and not a proxy for
model accuracy (this benchmark has no per-prediction accuracy signal to
expose; see "Limitations" below).

`feature_coverage_status` is the second, independent signal: are all
`state.feature_columns` values present (non-missing) for this date? In
the current 50×180 benchmark this is **always** `"complete"` (zero NaNs
across the full features table — a direct, verifiable consequence of the
`min_periods=1` design above), but the check is real and runs on every
request rather than being assumed — see "Feature-coverage status: real
now, valuable later" below.

No other signal was added. Model probability, exposure, liquidity, and
SHAP importance are all deliberately **excluded** from this policy: they
are the things being explained, not evidence about how much history backs
the explanation, and mixing them in would blur "how much data do we have"
with "what does the model say" — two different questions.

## The deterministic policy

`backend/risk/confidence_service.py:assess_confidence()`:

```python
HISTORY_PARTIAL_THRESHOLD_DAYS = ml.features.config.WINDOW_MEDIUM  # 28
HISTORY_FULL_THRESHOLD_DAYS = ml.features.config.WINDOW_LONG        # 60

if feature_coverage_status == "incomplete":
    confidence_level = "limited"
elif history_days >= HISTORY_FULL_THRESHOLD_DAYS:
    confidence_level = "high"
elif history_days >= HISTORY_PARTIAL_THRESHOLD_DAYS:
    confidence_level = "medium"
else:
    confidence_level = "limited"
```

| Level | Condition | Meaning |
|---|---|---|
| **High** | `history_days >= 60` and every feature present | Every trailing-window feature (7d/28d/60d) this merchant's risk score depends on is backed by its full intended window — not a shortened one. |
| **Medium** | `28 <= history_days < 60` and every feature present | The pipeline's primary 28-day windows (the same ones the simulator/intervention controls use) are fully backed, but the 60-day windows and the deviation-from-baseline features' expanding-history baseline are still computed on a shorter-than-intended history. |
| **Limited** | `history_days < 28`, **or** any required feature is missing | Even the primary 28-day windows are short by necessity, or a feature the model needs for this date genuinely isn't available. |

Both thresholds are imported directly from `ml/features/config.py` — never
redeclared — so this policy can never silently drift from the actual
feature pipeline's own window definitions, matching the same "single
source of truth" convention `backend/interventions/rules.py` established
for the simulator's control registry
(`docs/architecture/intervention_intelligence.md`).

**No new thresholds were invented for this task.** `28` and `60` are not
arbitrary — they are the exact window sizes `ml/features` already uses for
every trailing-window feature in the model, chosen for that purpose long
before this task existed.

## Response shape

`RiskResponse.data_quality` (always present on a real `/merchants/{id}/risk`
call):

```json
{
  "confidence_level": "high",
  "history_days": 180,
  "history_window_partial_days": 28,
  "history_window_full_days": 60,
  "feature_coverage_status": "complete",
  "reasons": ["...", "..."],
  "limitations": ["...", "..."],
  "basis": "...",
  "provenance": "derived"
}
```

- **`reasons`** — merchant-specific, built from the actual numbers for
  this request (e.g. exact `history_days`, exact feature count) — never a
  static template with placeholders left unfilled.
- **`limitations`** — two fixed, standing disclaimers, identical on every
  response: this is a prototype heuristic, not a statistical confidence
  interval or a model-calibrated probability; and this is a synthetic
  benchmark, so real-world validation is still pending.
- **`basis`** — a fixed sentence naming the exact method (thresholds and
  what was checked), for anyone who wants to verify the number by hand.
- **`provenance: "derived"`** — always. **Never `"modeled"`** — this is a
  transparent arithmetic/comparison result, computed the same way
  `liquidity_stress` is, not a second thing the ML artifact predicts. This
  is enforced structurally: the schema's `provenance` field is typed
  `Provenance`, and every code path in `confidence_service.py` returns the
  literal string `"derived"`.

## Feature-coverage status: real now, valuable later

`feature_coverage_status` is genuinely computed per-request against
`state.feature_columns` — not hardcoded to `"complete"` — but in the
current static 50×180 benchmark it will always evaluate to `"complete"`,
because `ml/features`' `min_periods=1` primitives guarantee no NaN ever
reaches the features table (see "Why these two signals" above). Stated
plainly rather than hidden: this specific branch of the policy is present
for **structural correctness and future-proofing** (a version of this
service pointed at a live feed with genuine missingness would need
exactly this check), not because it currently changes any merchant's
result in this benchmark. `tests/test_confidence.py` exercises the
`"incomplete"` branch directly with a small synthetic in-memory state
(not real benchmark data) to prove the code path is real and correctly
forces `confidence_level` to `"limited"` — the same technique
`recommendation_service.ranking_sort_key` is tested with in
`tests/test_interventions.py`.

## History-length variation: real, but only across dates, not across merchants at a fixed date

All 50 merchants in the current benchmark share the **exact same**
observed start date (2024-01-01) — a consequence of the generator's
"cold-start not modeled" design already documented in
`docs/architecture/feature_engineering.md` ("all merchants already have
full history from a fixed signup date before the observation window").
That means at any single fixed `as_of_date`, `history_days` — and
therefore `confidence_level` from the history-length branch — is
**identical across every merchant**. This is not a bug in the policy; it
is an honest consequence of how the benchmark was generated, stated here
rather than hidden.

The confidence signal still varies meaningfully — just along the
**date** axis, not the merchant axis, at any single query. Two facts from
the real 50×180 benchmark and the 140 injected risk/benign-growth events
make this concrete:

- At each merchant's **latest** observed date (day_index=179,
  history_days=180) — which is what the Overview page queries by
  default — confidence is **always** `"high"` for every merchant. This is
  the case a first-time user of the dashboard will typically see.
- At an **earlier** `as_of_date` — for example, an incident's own
  `detected_date`, which the incident layer already computes independently
  per episode (`docs/architecture/incident_response.md`) — real variation
  appears: of the 140 scenario events in the benchmark, 28 begin with
  fewer than 28 days of history and 48 begin with fewer than 60, so
  `"limited"` and `"medium"` are genuinely reachable, not just
  theoretical, if this assessment were ever computed at those dates. (V1
  intentionally scopes the visible surface to the Overview risk card only
  — see "Limitations" below for why incidents don't show a confidence
  badge yet.)

## API

No new endpoint. `data_quality` is a new section on the existing
`GET /merchants/{merchant_id}/risk` response, exactly the way `model`,
`exposure`, and `liquidity` are already sibling sections of the same
response — matching the task's explicit "do not create an unnecessary
standalone API" instruction and this project's established pattern of one
enriched, already-verified response over many small ones.

## AI Orchestrator integration

`SentinelAIContext.data_quality` (`DataQualityAIContext`) is a
byte-identical pass-through of the same `risk_result["data_quality"]`
`context_builder.py` already has in hand from its one
`risk_service.assess_risk()` call — no second computation, no second
service call. The assistant may explain `confidence_level` using exactly
the `reasons`/`limitations` already provided (system prompt rule 12,
`backend/ai/prompt.py`); it must never invent, calculate, or imply a
numeric/percentage confidence score (none exists), and must never upgrade
or downgrade the reported level itself. The mock provider's
`_confidence_answer()` demonstrates this: it echoes the real
`confidence_level` and `reasons` verbatim and explicitly states that no
percentage score is reported, even when directly asked for one (see
`tests/test_ai_orchestrator.py::test_mock_provider_never_fabricates_a_percentage_confidence_score`).

## Frontend

`ConfidenceBadge` (`components/overview/ConfidenceBadge.tsx`) is embedded
directly inside the existing `RiskSummary` card — not a new standalone
`MetricCard` section — so it reads as part of "how much should I trust
this risk read," not as another card competing for attention on an
already information-dense page. It shows a compact level badge (teal
"High" / slate "Medium" / amber "Limited" — **never red**, since this is
a data-sufficiency signal, not a risk warning) plus the existing
`ProvenanceTag` (always "Derived"), with the `reasons`/`limitations`/
`basis` text hidden behind a "Why this level" toggle — the same
expand/collapse pattern `InterventionRow` already uses for "Why this
matters," so a returning user recognizes the interaction immediately.

The frontend `RiskResponse.data_quality` field is typed **optional**
(`data_quality?: DataQualitySection`), unlike the backend's Pydantic
`RiskResponse` where it is always present. This is a deliberate,
documented asymmetry: `IncidentResponsePage.tsx` reuses `RiskSummary` via
a thin `IncidentDetail -> RiskResponse` type adapter
(`docs/architecture/incident_response.md`), and `IncidentDetail` does not
carry a `data_quality` section — Confidence/Data Quality V1 is scoped to
the Overview risk card only for this milestone. `RiskSummary` renders
`ConfidenceBadge` only when `risk.data_quality` is present, so the
Incident Response page's risk card renders exactly as it did before this
task, with no confidence badge and no error.

## Limitations

- **History-length variation is currently a date axis, not a merchant
  axis, at any single query** — see the dedicated section above. This is
  an honest property of the current benchmark generator, not a flaw in
  the policy.
- **`feature_coverage_status` never reaches `"incomplete"` in the current
  benchmark** — a real, tested, but not-yet-observed code path in
  production data; see "Feature-coverage status" above.
- **Not a model-calibration signal.** This says nothing about whether the
  30-day Random Forest's probability is well-calibrated for this
  merchant — that question is answered separately in
  `docs/research/baseline_ml_report.md` (calibration did not clearly
  improve the candidate) and is a property of the model, not of how much
  history exists.
- **Scoped to the Overview risk card only.** Incidents (evaluated at an
  earlier `detected_date`, where confidence would vary the most
  meaningfully) do not yet show a confidence badge — `IncidentDetail`
  does not carry a `data_quality` section in V1. See "Future extension
  path" below.
- **A prototype heuristic, not independently validated.** `history_days`
  vs. window size is a reasonable, inspectable proxy for "how much of the
  model's input is well-supported," but no separate analysis quantifies
  how strongly it correlates with actual prediction reliability in this
  benchmark — stated in `limitations` on every response, never hidden.
- **This is a synthetic-benchmark research prototype.** Nothing here is a
  claim about real-world data completeness, a real merchant's actual
  operational history, or a validated statistical confidence level.

## Future extension path (not implemented here)

- Surfacing `data_quality` on the Incident detail view (`IncidentDetail`
  schema, `IncidentResponsePage.tsx`) would make the real date-driven
  variation documented above visible where it actually occurs — a natural
  next step, deliberately out of scope for this V1 milestone.
- If a future signal source distinguishes merchants by actual signup
  timing within the observed window (rather than every merchant sharing
  2024-01-01), `history_days` would begin varying across merchants at a
  fixed date too, without any change to the policy itself — the rule
  already reads real per-merchant state, it simply has no per-merchant
  variation to read from in the current generator.
- A genuinely live feed with real missingness would make
  `feature_coverage_status: "incomplete"` a reachable, meaningful signal
  in practice, not just a tested-but-dormant code path.
