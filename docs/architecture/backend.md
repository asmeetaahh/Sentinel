# Backend Architecture

Source: [`backend/`](../../backend/)
Run with: [`scripts/run_backend.py`](../../scripts/run_backend.py)
Tests: [`tests/test_backend.py`](../../tests/test_backend.py)

## What this is

A thin, typed, read-only API over the already-validated research
artifacts. It trains nothing, retrains nothing, and does not duplicate the
research pipeline — it calls `ml.modeling` and `ml.explainability`
directly and adapts their outputs into HTTP responses.

```
data/{raw,processed,metadata}          (generator → features → labels)
        │
        ▼
data/metadata/modeling/artifacts/       (the saved, calibrated RF/30d artifact)
        │
        ▼
backend/api/state.py                    (loads tables + artifact + SHAP explainer ONCE at startup)
        │
        ▼
backend/services/ , backend/risk/       (typed access + risk/liquidity/explanation logic)
        │
        ▼
backend/api/routers/                    (FastAPI routes, request/response validation)
        │
        ▼
future dashboard
```

## Stack

**FastAPI + Pydantic v2 + uvicorn.** Nothing in the existing repo scaffold
(`backend/{api,risk,evidence,simulation,ai}` were empty placeholder
directories) dictated a different choice, and FastAPI gives typed
request/response validation, automatic OpenAPI docs (`/docs`), and async
support for free — a good fit for "clean typed responses" and future
extension. No database, no auth: the benchmark is a fixed, local, synthetic
dataset served read-only from disk; adding persistence/auth now would be
speculative infrastructure for a product need that doesn't exist yet (per
the explicit instruction not to over-engineer this).

## Directory layout

```
backend/
  api/
    main.py            FastAPI app, CORS, lifespan (loads state once at startup)
    state.py            AppState: tables + artifact + SHAP explainer + events, loaded once
    dependencies.py      FastAPI Depends() wiring to AppState
    routers/             health.py, merchants.py, risk.py, simulator.py, incidents.py, ai.py — thin HTTP adapters only
    schemas/              Pydantic request/response models
  services/
    merchant_service.py  merchant list/profile/observations/feature vector
    lookups.py            shared domain exceptions + date/merchant resolution
  risk/
    risk_service.py       model score/state + assembles the risk response
    liquidity_service.py  exposure estimate + liquidity stress derivation
    explainability_service.py   thin wrapper around ml.explainability
  simulation/
    controls.py            bounded what-if control registry — see docs/architecture/simulator.md
    simulation_service.py   modified-feature-vector what-if flow, same artifact
  evidence/
    reason_codes.py         synthetic prototype reason-code taxonomy + evidence requirements
    evidence_service.py     deterministic evidence-readiness engine
  incidents/
    incident_service.py     incident selection/assembly — see docs/architecture/incident_response.md
  ai/
    context_builder.py      assembles the one authoritative SentinelAIContext from existing services only
    guardrails.py            prompt-injection pre-filter + deterministic provenance/limitations/disclaimer
    prompt.py, response_parser.py, orchestrator.py
    providers/               provider-agnostic interface, mock (default) and OpenAI (lazy-imported) implementations
    — see docs/architecture/ai_orchestrator.md — the LLM is an explainer over verified context, never the risk engine
```

Routers contain no business logic — they call a service, catch its domain
exceptions, and translate them to HTTP status codes. Services contain no
HTTP-specific code — they can be unit-tested (and are) without spinning up
FastAPI.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/metadata` | Model artifact identity, horizon, dataset fingerprint, disclaimer |
| GET | `/merchants` | List all merchants (optional `archetype` filter) |
| GET | `/merchants/{id}` | Merchant profile + latest observed snapshot |
| GET | `/merchants/{id}/observations` | Historical daily observations (`start_date`, `end_date`, `limit`) |
| GET | `/merchants/{id}/features` | The 55-feature vector as of `as_of_date`, with manifest metadata |
| GET | `/merchants/{id}/risk` | Model risk score/state + exposure + liquidity stress, for `as_of_date` (+`horizon_days`, only `30` supported) |
| GET | `/merchants/{id}/explanation` | SHAP drivers for `as_of_date` (+`top_k`) |
| GET | `/merchants/{id}/simulation/controls` | Bounded what-if control bounds/baseline — see `docs/architecture/simulator.md` |
| POST | `/merchants/{id}/simulation` | Runs the same saved model on a modified feature vector — see `docs/architecture/simulator.md` |
| GET | `/merchants/{id}/incidents` | Summary list of this merchant's incidents — see `docs/architecture/incident_response.md` |
| GET | `/incidents/{incident_id}` | Full incident detail (risk/exposure/liquidity/drivers/evidence) |
| GET | `/incidents/{incident_id}/evidence` | Just the evidence-readiness section of an incident |
| POST | `/merchants/{id}/assistant` | Bounded AI assistant over verified context — see `docs/architecture/ai_orchestrator.md` |

Full request/response shapes are in `backend/api/schemas/` and enforced by
FastAPI at runtime (a malformed request → `422`, not a silent bad response).

## Errors

| Situation | Status | Notes |
|---|---|---|
| Unknown `merchant_id` | 404 | `MerchantNotFoundError` |
| `as_of_date` outside this merchant's generated history | 404 | `DateNotAvailableError`, message includes the valid range |
| Malformed query param (bad date format, etc.) | 422 | FastAPI/Pydantic validation, before any service code runs |
| `horizon_days` other than 30 | 400 | `UnsupportedHorizonError` — only the 30-day artifact is saved/loadable; see below |
| SHAP faithfulness check fails | 500 | Refuses to return an explanation it can't verify — see `ml/explainability` |

## Data provenance — observed / modeled / derived

Every risk-relevant field is explicitly tagged, per the task's emphasis on
this distinction:

- **`observed`** — read directly from the benchmark's generated data
  (`daily_observations.csv`, or `labels.csv`'s already-resolved future
  outcome for older dates). Includes `latest_observed_snapshot`,
  `available_liquidity`, and `retrospective_actual` exposure.
- **`modeled`** — the saved Random Forest artifact's output
  (`probability_calibrated`, `probability_raw_rf`) and its SHAP
  attributions. Never presented without the accompanying disclaimer that
  it is a synthetic-benchmark output, not a validated real-world
  probability.
- **`derived`** — computed transparently from the above, not by any ML
  model: the exposure `estimate` (trailing-average extrapolation) and
  `liquidity_stress` (`estimate / available_liquidity`, per
  `PROJECT_CONTEXT.md`'s own definition).

### Why exposure has two separate fields, not one

The baseline ML report (`docs/research/baseline_ml_report.md` §I) found
that a Random Forest regression candidate for `future_chargeback_amount`
did **not** outperform a simple trailing-average baseline, and no
regression artifact was ever saved. Rather than fabricate a "predicted
exposure" number from a model that isn't defensible, `exposure.estimate`
exposes the same deterministic trailing-average extrapolation used as the
research baseline — clearly labeled `derived`, with an explicit note that
it is not an ML prediction and why. `exposure.retrospective_actual`
separately exposes the benchmark's already-resolved future outcome (when
the window fits inside the generated 180 days) purely for research/
debugging comparison — explicitly marked as something a live deployment
could never have at prediction time.

### Liquidity stress

```
liquidity_stress = exposure.estimate.value / liquidity.available_liquidity.value
```

Computed in `backend/risk/liquidity_service.py`, exactly matching
`PROJECT_CONTEXT.md`'s definition, returned only when both inputs are
available (`null` with an explanatory note otherwise — e.g. zero
liquidity). It is a plain ratio, not a model output.

## Model / SHAP integration

- **Artifact**: `data/metadata/modeling/artifacts/random_forest_calibrated_30d.joblib`,
  loaded once via `ml.explainability.artifact.load_artifact()` — the exact
  same loader and validation used by the explainability research module
  (rejects the wrong horizon, wrong artifact type, or mismatched feature
  count at startup rather than at request time).
- **SHAP**: the `TreeExplainer` is built once at startup
  (`backend/api/state.py`) and reused for every `/explanation` request;
  each request still runs its own `compute_shap_values()` call and its own
  faithfulness check (`ml/explainability/shap_engine.py`) — a failed check
  raises rather than returning an unverified explanation.
- Both endpoints reuse `ml.modeling.datasets` to build the feature matrix
  — the identical code path the research pipeline uses, so the backend
  cannot silently drift from what was validated in
  `docs/architecture/feature_engineering.md`.

## CORS

Development-only origins (`localhost:3000`/`5173`, the common Next.js/Vite
dev ports) are allowed by a fixed list, plus `allow_origin_regex` for any
`localhost`/`127.0.0.1` port — Vite falls through to the next free port
(5174, 5175, ...) whenever its default is already taken locally, which the
fixed list alone can't anticipate. `GET` only, since the API is currently
read-only. Revisit when a real frontend origin/deployment target exists.

## Running locally

```bash
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/run_backend.py            # http://127.0.0.1:8000, auto-reload on
.venv/bin/python scripts/run_backend.py --port 8001 --no-reload

# Interactive docs: http://127.0.0.1:8000/docs
# Tests:
.venv/bin/python -m pytest tests/test_backend.py -v
```

Prerequisite artifacts must already exist (generate/build them first if
starting from a clean checkout, in order):
```bash
.venv/bin/python scripts/generate_dataset.py
.venv/bin/python scripts/build_features.py
.venv/bin/python scripts/run_baseline_ml.py
.venv/bin/python scripts/evaluate_calibration.py
```

## Limitations

- **Single model, single horizon.** Only the 30-day Random Forest has a
  saved artifact; 7-day and 14-day were evaluated in research
  (`baseline_ml_report.md`) but never persisted, so `horizon_days` other
  than 30 returns `400`, not a fabricated result.
- **No persistence, no auth.** Every response is derived fresh from
  in-memory, startup-loaded CSVs/artifacts. Fine for a local, synthetic,
  read-only benchmark; not evaluated for multi-user or production use.
- **Exposure is not a validated ML prediction** (see above) — it is an
  honestly-labeled arithmetic derivation, not equivalent in rigor to the
  classification model's output.
- **The classification model's own limitations still apply** — weak
  7-day/14-day signal, temporal-stress-test degradation at 30d,
  unresolved archetype-level disparities, calibration that did not clearly
  improve Brier score (all documented in `baseline_ml_report.md`). The
  backend surfaces the model faithfully; it does not fix or hide any of
  this.
- **This is a synthetic benchmark research prototype.** No claim of
  real-world predictive validity, no real Razorpay data or system access,
  and nothing here should be described as production-ready.
