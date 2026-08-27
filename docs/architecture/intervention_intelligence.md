# Intervention Intelligence + Merchant Risk Memory (V1)

Source: [`backend/interventions/`](../../backend/interventions/), [`backend/memory/`](../../backend/memory/), [`backend/api/routers/interventions.py`](../../backend/api/routers/interventions.py), [`apps/dashboard/src/components/interventions/`](../../apps/dashboard/src/components/interventions/)
Tests: [`tests/test_interventions.py`](../../tests/test_interventions.py), [`apps/dashboard/src/components/interventions/InterventionIntelligence.test.tsx`](../../apps/dashboard/src/components/interventions/InterventionIntelligence.test.tsx), [`apps/dashboard/src/components/interventions/RiskMemoryPanel.test.tsx`](../../apps/dashboard/src/components/interventions/RiskMemoryPanel.test.tsx)

## What this is

A deterministic decision layer sitting entirely on top of already-verified
Sentinel services — never a new model, never an LLM-generated
recommendation, never a claim about real-world effectiveness:

```
existing verified merchant state
    -> ml/features' own deviation-from-baseline z-scores (unmodified)
    -> existing SHAP contributors (unmodified explainability_service.explain)
    -> RULES registry (backend/interventions/rules.py) decides relevance + priority
    -> ranked recommendation list, each mapped 1:1 to an existing simulator control
    -> "Test in Simulator" hands off to the EXISTING, unmodified simulator
    -> merchant may optionally record a supported action/simulation state
    -> Merchant Risk Memory (in-process, session-scoped) stores what happened
    -> the actual real-world outcome remains "not_observed" — always
```

Nothing in this module computes risk, exposure, liquidity, SHAP values, or
simulated impact itself. It reads outputs of `ml/features`,
`backend/risk/explainability_service.py`, and `backend/simulation/`
verbatim and applies fixed, disclosed rules on top.

## Why no new ML model

The task explicitly forbids one, and there is no need for one: "is this
metric currently unusual for this specific merchant" is already answered
by an existing, unmodified feature — see "Relevance signal" below. Adding
a second model to answer a question the first one's own feature pipeline
already answers would be an unjustified, undocumented second source of
truth. `backend/interventions/rules.py` and
`backend/interventions/recommendation_service.py` import and read only;
they define zero new statistics.

## Relevance signal — reusing an existing feature, not inventing one

`ml/features/build_features.py` already computes, for each of the three
simulator-eligible metrics, a "deviation from this merchant's own recent
baseline" z-score (feature-engineering group 9,
`docs/architecture/feature_engineering.md`): the merchant's own trailing
7-day value of a 28-day-smoothed series, compared against **that same
merchant's own expanding-history mean/std**, clipped to `[-10, 10]`.

| Simulator control | Deviation feature read | "Bad" direction |
|---|---|---|
| `refund_rate_28d` | `refund_rate_deviation_z` | high is bad |
| `fulfillment_on_time_rate_28d` | `fulfillment_on_time_rate_deviation_z` | low is bad |
| `new_customer_rate_28d` | `new_customer_rate_deviation_z` | high is bad |

`backend/interventions/rules.py:signed_badness()` converts both
directions onto one signed scale where **larger is always more
concerning** — `+z` for a "high is bad" rule, `-z` for a "low is bad"
rule — so relevance and ranking share one consistent notion of severity.

### `RELEVANCE_Z_THRESHOLD = 2.0` — empirically chosen, not tuned for the UI

The threshold was chosen by inspecting the real distribution of these
three deviation-z features across the full 50×180 synthetic benchmark
(9,000 merchant-days), reproducible directly against
`data/processed/features.csv`:

```
refund_rate_deviation_z >= 2.0:               16.8% of rows
fulfillment_on_time_rate_deviation_z <= -2.0: 19.4% of rows
new_customer_rate_deviation_z >= 2.0:         18.2% of rows
```

That is roughly the most-deviated sixth-to-fifth of observations in the
"bad" direction for each control — a standard "meaningfully unusual, not
every-day noise" cut, not a number picked to make the dashboard look full
or empty. On the **latest observed day per merchant** (the snapshot the
Overview page actually queries), this threshold currently yields:

| Relevant controls that day | Merchants |
|---|---|
| 0 | 35 of 50 |
| 1 | 11 of 50 |
| 2 | 4 of 50 |
| 3 | 0 of 50 |

A genuinely selective bar: most merchants, most days, see the honest
empty state — see "Quality bar" below.

## Recommendation candidate construction

For each of the three `RULES` entries
(`backend/interventions/recommendation_service.py:get_recommendations`):

1. Read `deviation_z = feature_row[rule.deviation_feature]` for the
   merchant's feature row at `as_of_date` (defaults to that merchant's
   latest observed date if omitted).
2. Skip the control unless `is_relevant(rule, deviation_z)` — i.e.
   `signed_badness(rule, deviation_z) >= RELEVANCE_Z_THRESHOLD`.
3. For a relevant control, build a candidate carrying:
   - `current_value` — the control's own observed baseline, straight from
     `simulation_service.list_controls` (never redeclared).
   - `deviation_z` — the raw value plus a `method` string naming the exact
     feature and its definition.
   - `shap_corroboration` — see below.
   - `reason` — one merchant-facing sentence, built entirely from the
     above (see "Wording" below); never free text, never LLM-generated.
   - `simulator_control` — the exact `ControlMeta` the simulator itself
     would report for this control (bounds, feature name, group,
     description) — the literal handoff object for "Test in Simulator."
   - `modeled_impact_reminder` — a fixed, non-causal disclaimer string,
     identical for every recommendation.

A merchant with zero relevant controls gets `count: 0`,
`recommendations: []`, and a fixed `empty_state_note` explaining why — see
"Empty state" below. **The three controls are never all shown by
default**; each is independently gated by its own deviation check.

### SHAP corroboration — the second, independent signal

Priority is not derived from the deviation magnitude alone. Each
recommended control's simulator `group` (`refund_behavior`, `fulfillment`,
or `customer_mix` — from the single existing
`backend/simulation/controls.py` registry) is checked against the
existing, unmodified `explainability_service.explain(...,
top_k=5)['all_contributors']`: is any feature in that same behavior group
currently one of this merchant's verified SHAP contributors pushing risk
*higher*?

- **`priority: "high"`** — corroborated: the observed deviation and the
  model's own verified explanation agree.
- **`priority: "medium"`** — not corroborated: the deviation is real and
  observed, but the model's current explanation doesn't (yet) implicate
  that behavior group.

There is no `"low"` tier — a control that isn't relevant is not shown at
all, so every recommendation that exists is already worth a look; SHAP
corroboration only decides how strongly to emphasize it. This is a
genuine second, independent signal (observed deviation vs. modeled
explanation), not a cosmetic label — `shap_corroboration.note` states
exactly what was checked, and `provenance: "modeled"` marks it as coming
from SHAP, distinct from the `derived` deviation-z and `observed` current
value.

## Ranking and deterministic tie-breaking

`ranking_sort_key()` (extracted standalone, directly unit-testable
against synthetic inputs independent of any real merchant's data):

```python
(candidate["priority"] != "high", -candidate["_sort_badness"], candidate["control_id"])
```

1. **High priority sorts before medium** (`False < True` in Python, so
   `priority != "high"` is `False` for high-priority candidates).
2. **Within the same tier, larger `signed_badness` (bigger deviation in
   the "bad" direction) sorts first.**
3. **Final deterministic tiebreak: `control_id`, fixed alphabetic order**
   (`fulfillment_on_time_rate_28d` < `new_customer_rate_28d` <
   `refund_rate_28d`) — only reachable on a coincidental exact
   deviation-z match, but present so ordering is fully deterministic
   either way, never insertion-order-dependent.

After sorting, `priority_rank` is assigned `1..N` in final order and the
internal `_sort_badness` scratch field is removed before the response is
built — it never appears in the API response.

## Wording — merchant-facing, concise, and never causal

`_build_reason()` builds one sentence per recommendation, entirely from
already-known values:

```
"{metric_label} is currently {current_value:.1%}, which is {|deviation_z|:.1f}
standard deviations {above|below} this merchant's own recent historical baseline."
```

plus, only when SHAP-corroborated, one appended sentence naming that the
behavior group is also among the model's currently verified contributors.
The three titles (`RULES[control_id].title`) are fixed, one per control:
**"Review refund pressure,"** **"Review fulfillment reliability,"**
**"Review customer-mix shift."** Every recommendation also carries the
fixed `modeled_impact_reminder`, which states plainly that this is an
observed deviation, not a claim that changing the control will reduce
real-world risk, and points at the simulator for testing modeled impact.
Nothing here ever says "guaranteed," "will reduce," "causes," or
"expected savings" — enforced by `tests/test_interventions.py`'s
forbidden-language checks across every recommendation and memory field.

## Empty state — an honest, expected, common outcome

`EMPTY_STATE_NOTE` (a single fixed string) is returned whenever no
control clears the relevance bar — the common case for the majority of
merchant-days in this benchmark (see the 35/50 table above). The frontend
(`InterventionIntelligence.tsx`) renders this via the same `EmptyState`
component used elsewhere in the product, not a special-cased "coming
soon" placeholder — an empty recommendation list is a real, correct
answer, not a missing feature.

## Relationship to the existing simulator — no second simulation engine

Each recommendation's `control_id` is one of the exact three IDs already
defined in `backend/simulation/controls.py`'s `CONTROLS` registry
(`docs/architecture/simulator.md`) — `RULES` never redeclares a control's
feature, bounds, label, or group; it only adds intervention-specific
metadata (`deviation_feature`, `direction`, `title`) keyed by the same
`control_id`. `simulator_control` in every recommendation response is the
literal `ControlMeta` object `simulation_service.list_controls` would
return for that control at that date — not a copy or a redeclaration.

**"Test in Simulator"** (`InterventionRow.tsx`) is a plain
`react-router-dom` link to `/simulator?control=<control_id>` — client-side
navigation only, no new backend call. `SimulatorPage` reads the
`control` query parameter via `useSearchParams()` and passes it down as
`highlightedControlId`, which `ControlsPanel` → `ControlSlider` uses to
apply a visual ring highlight to the matching slider — a UI affordance
only; every control remains independently editable and the simulator's
own request/response contract, bounds, and mathematics are completely
unchanged. The simulator remains the sole source of any counterfactual
numerical result — Intervention Intelligence never computes, caches, or
approximates a modeled-impact number itself.

No sibling control is ever pre-filled or auto-adjusted when a
recommendation deep-links into the simulator — the existing simulator's
"do not cascade sibling features" behavior
(`docs/architecture/simulator.md`) is untouched.

## Merchant Risk Memory V1

A structured, in-process record of intervention-related activity — not a
database, not a learning system, not a source of real outcomes.

### Data model

Each record (`backend/api/schemas/interventions.py:InterventionMemoryRecord`):

| Field | Meaning | Source |
|---|---|---|
| `intervention_id` | `f"{merchant_id}:{control_id}:{as_of_date}"` | Parsed from the client-supplied id; must match a format this backend itself could have produced |
| `merchant_id`, `control_id` | Parsed out of `intervention_id` | Validated against `RULES` and the merchant's own real observed dates |
| `recommendation_title` | The control's fixed title | Looked up server-side from `RULES[control_id].title` — **never accepted as client text** |
| `action_status` | `reviewed` \| `simulated` \| `acknowledged` \| `dismissed` | Client-selected, but only from this fixed enum |
| `timestamp` | UTC record time | `datetime.now(timezone.utc)`, server-assigned |
| `simulated_impact` | A modeled-impact summary, or `null` | Re-computed server-side by re-running the real simulator (see below); never client-supplied numbers |
| `outcome_status` | Always `"not_observed"` | Hardcoded server constant — no field, parameter, or code path can set it to anything else |
| `outcome_note` | Fixed explanatory sentence | Always the same `OUTCOME_NOTE` string |

### The three concepts this module is careful never to conflate

1. **Simulation** — a modeled result from the existing, unmodified
   simulator (`simulation_service.simulate`). Purely hypothetical, always
   labeled `MODELED IMPACT`.
2. **Merchant action** — `action_status`: has the merchant reviewed,
   simulated, acknowledged, or dismissed this recommendation in this
   session? This is a record of **engagement**, not of a real-world
   business change having actually happened.
3. **Actual observed outcome** — a real post-intervention result. **This
   benchmark cannot provide one** (no post-intervention data collection
   exists in the synthetic dataset). `outcome_status` therefore has
   exactly one possible value, `"not_observed"`, for every record this
   system will ever produce, and `outcome_note` states this limitation on
   every single record — never hidden, never only in documentation.

### Recording a simulation — trust boundary

When `action_status == "simulated"`, a `simulation` body
(`SimulationRequest` — the exact same bounded shape `/merchants/{id}/simulation`
itself accepts) is required. The service:

1. Validates `simulation.as_of_date` matches the recommendation's own
   `as_of_date`, and that the recommended `control_id` is among the
   simulation's changed controls (`SimulationDateMismatchError`,
   `SimulationControlMismatchError` otherwise).
2. **Re-runs the real, unmodified `simulation_service.simulate()`
   server-side** — the client's own simulation result (already fetched by
   the frontend to display it) is never trusted or accepted as input, only
   the bounded control values are. This mirrors the exact pattern already
   used by `backend/ai/context_builder.py`'s `_simulation_context()` for
   the AI assistant.
3. Stores the resulting probability/exposure/liquidity-stress
   current-vs-simulated numbers, all carrying `provenance: "modeled"`.

`action_status` values other than `"simulated"` must **not** include a
`simulation` body (`SimulationNotApplicableError`) — a plain
acknowledgement carries no modeled-impact number to avoid implying one
was tested when it wasn't.

### Why in-process, not a database

Consistent with this milestone's explicit "no database" instruction and
every other Sentinel table's existing loading pattern
(`backend/api/state.py`), the store is one more field on the same shared
`AppState`:

```python
memory_store: dict[str, list[dict]]  # merchant_id -> chronological records
```

Initialized empty in `load_state()`, reset by the same
`reset_state_for_tests()` every other in-memory table already uses. It is
naturally cleared on process restart — stated plainly in the product UI
(`RiskMemoryPanel`'s intro line: "A lightweight, in-process record of
intervention activity for this session only ... This is a prototype
decision history, not a validated learning system") and in this document.
This is a deliberate V1 scope limit, not an oversight — see "Limitations"
below for what a real version would need.

### Empty state

`GET /merchants/{id}/interventions/memory` for a merchant with no records
returns `count: 0`, `records: []`, and a fixed `EMPTY_MEMORY_NOTE`
explaining that recording is optional and merchant-initiated — no
fabricated history is ever synthesized to populate the UI.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/merchants/{merchant_id}/interventions?as_of_date=...` | This merchant's ranked recommendation list (or the empty state) |
| GET | `/merchants/{merchant_id}/interventions/memory` | This merchant's Risk Memory records (or the empty state) |
| POST | `/merchants/{merchant_id}/interventions/memory` | Record one supported action/simulation state |

`RecordInterventionRequest` (`extra="forbid"`) accepts only
`intervention_id`, `action_status`, and an optional `simulation` body —
there is deliberately no `recommendation_title` or `outcome_status` field
on the request type at all, so a client cannot inject fabricated
recommendation text or an observed outcome even by accident. Unknown
merchant/date → 404; malformed `intervention_id`, cross-merchant id,
unknown control, action/simulation mismatches, out-of-range simulation
controls → 422. Merchant isolation is enforced both by construction
(`intervention_id` embeds and is checked against `merchant_id`) and by
`state.memory_store` being keyed per merchant.

## AI Orchestrator integration

The AI Orchestrator (`docs/architecture/ai_orchestrator.md`) gained one
new, always-computed context field —
`SentinelAIContext.interventions: list[InterventionRecommendationAIContext]`
— built the same way `drivers` already is, by calling the unmodified
`recommendation_service.get_recommendations()`. The assistant may
**summarize or explain** an existing recommendation's `reason` verbatim;
the system prompt explicitly forbids it from inventing a new
recommendation, a different control, a reason not already given, an
outcome, a success rate, or a claim that Sentinel has "learned" from Risk
Memory — because V1 memory contains no real outcomes to learn from. See
`docs/architecture/ai_orchestrator.md` for the exact prompt rules added.

## Frontend

`InterventionIntelligence` (Overview page, after `RiskDrivers`) renders
the ranked list via `InterventionRow` — priority badge, optional "Verified
SHAP driver" badge, title, reason, an expandable "Why this matters"
(deviation method + SHAP note + the modeled-impact reminder), a "Test in
Simulator" link, and an "Acknowledge" action that calls the record
endpoint with `action_status: "acknowledged"` — or the honest empty state.
`RiskMemoryPanel` (directly below it) renders records newest-first, each
with its action-status badge, an always-present "Outcome: Not observed"
badge (`OUTCOME_STATUS_STYLE`, deliberately muted — never styled as a
warning or a success), the modeled probability line when a simulation was
attached, and the outcome note — or its own honest empty state. On the
Simulator page, `RecordSimulationInMemory` is offered only when the
just-run simulation touched exactly the one control a currently-active
recommendation names (a multi-control simulation has no single
`intervention_id` to attach to) — a deliberate, documented scope limit,
not an oversight.

Color usage stays restrained, matching the rest of the product: priority
reuses the existing amber/slate `PRIORITY_STYLE` (no red for "high" —
red stays reserved for elevated risk state), and the new
`ACTION_STATUS_STYLE`/`OUTCOME_STATUS_STYLE` maps are deliberately muted
— "not observed" is a calm fact of this prototype's design, never an
alarm.

## Limitations

- **In-process, not durable.** `state.memory_store` resets on every
  backend restart and is not shared across multiple backend processes —
  a genuine V1 scope limit for a no-database prototype, stated in the UI
  itself.
- **No real outcomes exist to learn from.** `outcome_status` has exactly
  one value for every record and always will, until a legitimate
  post-intervention data source exists. This system does not calculate
  success rates, does not claim to have learned anything from past
  recommendations, and does not use Risk Memory as an input to future
  recommendations — `get_recommendations()` never reads `memory_store`.
- **Relevance and priority are prototype heuristics**, grounded in real
  observed/modeled signals (deviation-z, SHAP corroboration) but not
  independently validated as "the right" intervention-prioritization
  rule — stated in `modeled_impact_reminder` on every recommendation.
- **Only the three existing bounded simulator controls** are ever
  candidates — no other operational lever is represented, by design.
- **This is a synthetic-benchmark research prototype.** Nothing here is a
  claim that reviewing, testing, or acting on a recommendation causes any
  change in real-world risk, or that Sentinel has observed, measured, or
  validated any real post-intervention outcome.

## Future extension path (not implemented here)

- A real outcome data source (e.g. actual post-intervention chargeback
  data, once available) could populate `outcome_status` with genuine
  values beyond `not_observed` — the schema's `Literal["not_observed"]`
  would need to grow, and only then would any success-rate or
  learning-from-history calculation become honest to build.
- Durable, cross-process storage (a real database) if Risk Memory needs
  to survive a restart or be shared across backend instances — explicitly
  out of scope for this milestone.
- Additional simulator controls, if `docs/architecture/simulator.md`'s own
  control registry ever grows, would need corresponding `RULES` entries —
  `recommendation_service.py` deliberately loops over `RULES.items()`
  rather than hardcoding three checks, so this is a registry addition,
  not a rewrite.
