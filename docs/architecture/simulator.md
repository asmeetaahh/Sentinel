# What-If / Counterfactual Simulator

Source: [`backend/simulation/`](../../backend/simulation/), [`backend/api/routers/simulator.py`](../../backend/api/routers/simulator.py), [`apps/dashboard/src/pages/SimulatorPage.tsx`](../../apps/dashboard/src/pages/SimulatorPage.tsx)
Tests: [`tests/test_simulator.py`](../../tests/test_simulator.py), [`apps/dashboard/src/pages/SimulatorPage.test.tsx`](../../apps/dashboard/src/pages/SimulatorPage.test.tsx)

## What this is

A bounded, deterministic what-if tool: a merchant edits a small number of
their own trailing operational metrics and sees how the **exact same
saved** Random Forest / 30-day artifact — the one `/merchants/{id}/risk`
already uses — responds, plus how the transparently-derived exposure and
liquidity-stress view moves as a result.

```
current feature vector (observed, from ml.features)
    -> bounded user intervention on 1-3 controls (backend/simulation/controls.py)
    -> modified feature vector (every other of the 55 features held fixed)
    -> the SAME artifact.calibrated_pipeline / artifact.base_random_forest
       (backend/api/state.py — no retraining, no new artifact)
    -> new model output
    -> illustrative exposure scaling + liquidity stress
    -> comparison against the current state
```

Everywhere in the product this is labeled **MODELED IMPACT** — never
"guaranteed savings," "will reduce," or any other causal/guaranteed
phrasing. It is a bounded model what-if, not causal inference: it shows
what the same classifier says under a different, bounded input, not what
would actually happen if the merchant changed its real operations.

## Why only three controls

`ml/features/build_features.py` produces 55 features; only three are
exposed as simulator controls (`backend/simulation/controls.py`):

| Control | Feature edited | Group |
|---|---|---|
| Refund rate (trailing 28 days) | `refund_rate_28d` | refund_behavior |
| On-time fulfillment rate (trailing 28 days) | `fulfillment_on_time_rate_28d` | fulfillment |
| New-customer share (trailing 28 days) | `new_customer_rate_28d` | customer_mix |

Two deliberate filters produced this list, both explained in
`backend/simulation/controls.py`'s module docstring:

1. **Maps to exactly one existing feature, unmodified.** No new feature is
   invented and no existing feature's definition is changed —
   `docs/architecture/feature_engineering.md` remains the single source of
   truth for what each of these columns means.
2. **Represents an operational lever, not a proxy for the outcome itself.**
   The task named refund behavior, fulfillment performance, and customer
   mix explicitly as candidate levers. Chargeback-rate features were
   deliberately **excluded**: a merchant cannot "set" their own past
   chargeback rate the way they can act on refund handling or fulfillment
   execution — chargeback-rate features are closer to a proxy for the
   outcome being predicted than to a controllable input, and exposing them
   as a slider would read as "predict chargebacks by inputting
   chargebacks," not as a genuine what-if.

The 28-day window was chosen over 7d/60d for all three controls because
it is the feature pipeline's own primary window and gives the clearest
"current sustained level" framing for a slider.

## Why the simulator does NOT cascade-update sibling features

Each control edits **exactly one** feature column. It does not also
adjust that metric's 7d/60d windows, its velocity/acceleration
(`refund_rate_velocity_7v28`, etc.), or its deviation-from-baseline z-score
(`refund_rate_deviation_z`) — even though those are mathematically related
to the edited feature.

This was a deliberate choice, not an oversight. Consistently updating
those siblings would require either:
- fabricating a full alternate 28-90 day daily history to re-run
  `ml/features` against (explicitly forbidden — "do not fabricate
  transaction-level data"), or
- inventing an ad hoc cascading-update rule (e.g. "shift the 60d window by
  a fraction of the 28d change") for which no validated methodology
  exists in this project.

Leaving every other feature at its observed value — and documenting that
plainly — is the more honest choice than quietly inventing a plausible-
looking but unvalidated cascade. It is also the standard convention for
this class of interpretability tool: this is effectively a bounded,
single/few-feature partial-dependence-style query against the model, not
a full alternate-history re-simulation.

## Control bounds

Bounds are computed at request time from the loaded benchmark, not
hardcoded:

```python
min_value, max_value = float(state.features[feature].min()), float(state.features[feature].max())
```

This is the full observed range of that feature across every merchant and
day in the 50×180 synthetic benchmark. A submitted value outside
`[min_value, max_value]` is rejected with a 422 — the simulator refuses to
ask the model to extrapolate beyond values it has ever seen at either
training or evaluation time. This bound is deliberately **not** narrowed
to the individual merchant's own history: a merchant-specific range would
often be too narrow to explore anything interesting, and the benchmark-
wide range is the honest "has the model ever seen this" question.

## Exposure under simulation — a documented derived scaling, not a new model

`/merchants/{id}/risk`'s exposure estimate is a trailing-28-day mean daily
chargeback-amount extrapolation (`docs/architecture/backend.md`) —
computed entirely from **observed** daily data, independent of the ML
feature vector. It cannot simply be "re-run" under a hypothetical feature
edit the way the classifier can, because no regression model produced it
in the first place (the RF regression candidate evaluated in research did
not outperform this baseline and was never saved — see
`docs/research/baseline_ml_report.md` section I).

Rather than leave the simulated exposure identical to the current exposure
(making the exposure comparison always show "no change," which would defeat
the point of a what-if tool) or invent a new, unvalidated regression
number, the simulator applies one explicit, disclosed, deterministic
transformation:

```
risk_ratio = simulated_probability_calibrated / max(current_probability_calibrated, 1e-4)
simulated_exposure = current_exposure_estimate * risk_ratio
```

This reuses the classifier's own probability shift — the one thing that
*was* validated — to scale the same observed baseline the `/risk` endpoint
already reports, rather than fabricating an independent exposure forecast.
The `1e-4` floor exists only to prevent a division blowup when the current
probability is at or near zero; it is fixed and never tuned per-request.
Every exposure value returned by the simulator carries `provenance:
"derived"` and a `method` string spelling this out — never presented as a
model prediction. `liquidity_stress` is then the same
`exposure / available_liquidity` formula `/risk` already uses, applied to
the simulated exposure.

**Limitation, stated plainly:** this assumes exposure scales
proportionally with the classifier's probability shift. That assumption
has not been separately validated — it is a transparent illustrative
convention, not a second model. Treat the exposure/liquidity-stress
columns as directionally informative, not as a precise dollar forecast.

## Request / response shape

`GET /merchants/{id}/simulation/controls?as_of_date=...` returns the three
controls' bounds and this merchant's current baseline value for each —
what the frontend uses to initialize sliders.

`POST /merchants/{id}/simulation` accepts a fixed-shape body (not a
generic dict) with `as_of_date`, an optional `horizon_days` (only `30` is
supported, matching `/risk`), and up to three optional float fields —
`refund_rate_28d`, `fulfillment_on_time_rate_28d`, `new_customer_rate_28d`
— each `Field(allow_inf_nan=False)`. At least one must be set (enforced by
a Pydantic model validator); an unknown field is rejected outright
(`extra="forbid"`). The response reports `current` and `simulated` model
output, exposure, and liquidity stress side by side, plus `absolute`/
`relative` deltas, the applied controls (baseline vs. simulated value,
bounds, feature name), and the `modeled_impact_disclaimer`.

The endpoint is deterministic: identical input produces identical output,
since it only ever calls `predict_proba` on the already-fit, already-saved
artifact — no randomness, no retraining, no state mutation.

## What the backend guarantees, and how it's tested

`tests/test_simulator.py` verifies, against the real loaded artifact (not
a mock):

- **Feature ordering and isolation** — a manually-built comparison feature
  row (same base row, only the target index changed) reproduces the
  service's own `probability_calibrated`/`probability_raw_rf` output
  exactly, and every non-target feature is proven byte-identical to the
  observed baseline.
- **Same artifact, not a new model** — the "current" output from
  `simulate()` matches a direct `predict_proba` call on the unmodified
  feature row.
- **No mutation** — `state.features` (the shared, startup-loaded table) is
  byte-identical before and after several simulation calls across
  different merchants.
- **Merchant isolation** — each merchant's "current" baseline in a
  simulation matches that merchant's own `/risk` response; two merchants'
  baselines are not accidentally equal.
- **Determinism** — identical requests (at both the HTTP and Python level)
  return byte-identical responses.
- Schema validation, out-of-range/unknown-control/no-control 422s,
  unsupported-horizon 400, unknown-merchant/date 404s, provenance
  correctness, and the absence of forbidden causal/guaranteed language.

## Frontend

`SimulatorPage` fetches the controls baseline, renders three sliders
(`ControlSlider`, bounded to the server-reported min/max, with a tick mark
at the observed baseline), and only sends a control in the POST body if
its value differs from baseline (`lib/simulationRequest.ts`) — an
untouched slider is omitted, not "sent as unchanged." "Run simulation" is
disabled until at least one control has actually moved, so a no-op request
(which the backend would reject) is never attempted. "Reset to observed
values" restores every slider to baseline and clears any prior result.
`SimulationResult` shows a prominent "MODELED IMPACT" badge, a risk-state
comparison, a current/simulated/change table (probability, exposure,
liquidity stress), the changed controls, and the same causality disclaimer
verbatim from the API — never LLM-generated, never re-worded.

## Limitations

- **Single/few-feature edits, not a full re-simulation.** See "Why the
  simulator does NOT cascade-update sibling features" above.
- **Exposure scaling is an illustrative convention**, not a second
  validated model — see the dedicated section above.
- **Only the 30-day horizon** has a saved artifact, matching `/risk`'s own
  limitation (`docs/architecture/backend.md`).
- **Bounds are benchmark-wide, not merchant-specific** — a control's
  slider range reflects what the model has seen anywhere in the 50×180
  synthetic benchmark, not necessarily what is realistic for this one
  merchant's own history.
- **This is a synthetic-benchmark research prototype.** Nothing here
  should be read as a forecast of real-world outcomes, a recommendation to
  take a specific business action, or a claim that any control causes a
  change in real-world risk.
