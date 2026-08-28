<div align="center">

# Sentinel

**A merchant-facing risk intelligence prototype that turns early chargeback-risk signal into explainable, financially meaningful, bounded operational decisions.**

*Independent research prototype — Razorpay Buildathon, Track 02 (AI Risk Manager)*

[Live Product](#) · [3D Marketing Website](#) · [Pitch / Demo Video](#) · [Research Journey](docs/research/RESEARCH.md)

</div>

---

## 1. Sentinel

Sentinel is an independent research prototype that predicts **materially
elevated future chargeback-loss exposure** for a merchant, explains what
is driving it, translates it into cash-flow and liquidity terms, lets a
merchant test bounded operational changes before acting, and prepares
them to respond if the risk actually materializes.

It is a research-backed AI Risk Manager built end-to-end — synthetic
benchmark, evaluated ML, a typed backend, a working dashboard, and a
grounded AI layer — not a mockup or a slide deck. It makes no claim to
Razorpay's proprietary data, risk systems, or dispute infrastructure.

---

## 2. The Problem

A chargeback is not experienced by a merchant as a single scored
transaction. It is experienced as a trend: is risk getting worse, why,
what would it cost if it continues, is there time to act, and — if not
— is the merchant ready to respond. Most existing infrastructure sits
at the transaction-decisioning or after-the-fact response layer (see
[`docs/research/RESEARCH.md` §2](docs/research/RESEARCH.md)). Sentinel
investigates the layer in between: **merchant-level, forward-looking
decision intelligence**, not another transaction score.

This is presented as the problem Sentinel's research investigated, not
as a proven or externally validated market gap.

---

## 3. What Sentinel Does

```
Risk detection → Explainability → Exposure / Liquidity → What-if Simulation
    → Intervention Intelligence → Incident Response → Evidence Readiness
    → Risk Memory / Outcome Loop
```

| Stage | Status |
|---|---|
| Risk detection (30-day horizon, provisional benchmark candidate) | **Implemented** |
| Explainability (SHAP, faithfulness-verified) | **Implemented** |
| Exposure / liquidity translation | **Implemented** (transparent derivation, not a second model) |
| What-if simulator (3 bounded controls) | **Implemented** |
| Intervention Intelligence (deterministic V1 rules) | **Implemented** |
| Incident Response (detection → reason code → response prep) | **Implemented** |
| Evidence Readiness | **Implemented** |
| AI Orchestrator (grounded assistant) | **Implemented** |
| Risk Memory (records activity; outcome always `not_observed`) | **Implemented as scaffolding — not a self-learning loop** |
| Real-outcome learning loop | **Future research direction — not built** |

Full behavior and scope: [`PRODUCT.md`](PRODUCT.md).

---

## 4. Research-Backed Approach

Sentinel was not built from a fixed feature list. It followed an
explicit research process — including a deliberate attempt to falsify
its own thesis before writing product code:

```
Question → Landscape → Falsification → Hypothesis → Experiment → Results → Failure Analysis → Product
```

The full narrative — including the counter-hypotheses considered, what
survived, and what did not — is documented in
[`docs/research/RESEARCH.md`](docs/research/RESEARCH.md). It is not
reproduced here.

---

## 5. Benchmark / Evaluation

All results are evaluated on a **fully synthetic, reproducible
benchmark**: 50 merchants × 180 days, one fixed seed, 8 merchant
archetypes, 140 scheduled scenario events, 55 engineered features. No
real Razorpay or merchant data is used anywhere in this repository.

| Result | Value |
|---|---|
| PR-AUC, Random Forest, 7d / 14d / 30d | 0.262 / 0.370 / 0.603 |
| PR-AUC, 30d, temporal stress test (later, unseen period) | 0.603 → **0.476** |
| Median warning lead time, 30d (after a measurement bug fix) | **7.0 days** |
| Brier score, uncalibrated vs. calibrated (30d) | 0.188 → **0.192 (no improvement)** |
| Hard-negative (growth ≠ risk) behavior | Holds in aggregate; **fails on one scenario type** (100% false-positive rate, small sample) |
| Exposure regression vs. a trailing-average baseline | **Beaten by the simpler baseline** — no regression artifact shipped |

Predictive separation increases materially with horizon; 7-day
prediction remains weak. The selected candidate degrades under
temporal drift rather than surviving it cleanly. Calibration and
exposure regression are reported as **negative results**, not hidden.

**This is synthetic-benchmark evidence. It does not establish
production performance, real-merchant validity, or causal effect of
any intervention or simulator output.** Full methodology, every metric,
and the complete failure analysis: [`EVALUATION.md`](EVALUATION.md).

---

## 6. Product Architecture

```
Synthetic Benchmark + ML Artifacts
        → Risk Engine
        → Explainability / Exposure / Liquidity
        → Counterfactual Simulator
        → Intervention Intelligence
        → Incident Response → Evidence Readiness
        → AI Orchestrator (explains verified state — never computes risk itself)
        → Merchant Risk Memory
```

The system that computes risk is kept structurally separate from the
system that explains it — the AI layer never writes into a risk,
exposure, liquidity, SHAP, simulation, or incident value. Full
implementation-level design: [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 7. Repository Structure

```
sentinel/
├── apps/dashboard/     React + TypeScript dashboard (6 screens)
├── backend/            FastAPI backend — risk, simulation, incidents,
│                        evidence, interventions, memory, AI orchestrator
├── data/                Generated synthetic benchmark, features, ML artifacts
├── docs/
│   ├── architecture/    Per-module implementation design docs
│   └── research/        Research journey + full research/evaluation reports
├── ml/                  Data generation, feature engineering, modeling,
│                        explainability, validation
├── scripts/             Generate data, build features, train/evaluate, run backend
├── tests/                Python test suite (backend, ML, AI orchestrator)
├── ARCHITECTURE.md      System architecture
├── EVALUATION.md        Quantitative evaluation and failure analysis
├── PRODUCT.md           Product behavior and scope
├── PROJECT_CONTEXT.md   Original project brief / engineering philosophy
├── README.md            This file
└── SECURITY.md          Security / data-handling notes
```

---

## 8. Running Sentinel Locally

### Backend

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt

# Build the benchmark and ML artifacts once, in order (if not already present):
.venv/bin/python scripts/generate_dataset.py
.venv/bin/python scripts/build_features.py
.venv/bin/python scripts/run_baseline_ml.py
.venv/bin/python scripts/evaluate_calibration.py
.venv/bin/python scripts/run_explainability.py

# Start the API
.venv/bin/python scripts/run_backend.py --port 8010
# Interactive docs: http://127.0.0.1:8010/docs
```

macOS also requires `brew install libomp` for XGBoost (research/training
scripts only, not the served backend — see `requirements.txt`).

### Frontend

```bash
cd apps/dashboard
cp .env.example .env        # VITE_API_BASE_URL — point this at the backend port above
npm install
npm run dev                  # http://localhost:5173 (or next free port)
```

### Checks

```bash
# Python
.venv/bin/python -m pytest tests/ -v

# Frontend (from apps/dashboard/)
npx vitest run
npx tsc -b --noEmit
npm run lint
npm run build
```

### Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `SENTINEL_AI_PROVIDER` | repo root `.env` | `mock` (default, no network calls) \| `openai` \| `featherless` |
| `OPENAI_API_KEY`, `SENTINEL_AI_MODEL` | repo root `.env` | Only if using the real OpenAI provider |
| `FEATHERLESS_API_KEY`, `FEATHERLESS_BASE_URL`, `FEATHERLESS_MODEL` | repo root `.env` | Only if using the Featherless.ai provider |
| `VITE_API_BASE_URL` | `apps/dashboard/.env` | Backend URL the dashboard calls |

See `.env.example` and `apps/dashboard/.env.example`. Never commit a
real API key — both example files are gitignored placeholders.

---

## 9. Technology

- **Backend**: Python, FastAPI, Pydantic v2, uvicorn — typed, read-only
  API over the research artifacts.
- **ML**: numpy, pandas, scikit-learn, XGBoost, SHAP.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, recharts,
  react-router-dom.
- **Testing**: pytest (backend/ML), Vitest + Testing Library (frontend).
- **AI providers**: a deterministic mock provider (default, no network
  dependency); OpenAI; Featherless.ai (OpenAI-compatible, open-weight
  models) — both real providers optional and lazily loaded.

No database and no auth layer exist — the backend serves a fixed,
local, synthetic dataset read-only from disk.

---

## 10. AI / Assistant Honesty

Sentinel's assistant explains **already-computed** risk, exposure,
liquidity, SHAP drivers, simulations, and incidents. It does not, and
structurally cannot, calculate a risk score itself — every number it
discusses is computed by an existing service before the AI provider is
ever called, verified byte-identical to the same authoritative call
every dashboard screen makes.

Every value Sentinel shows is labeled by provenance:

| Label | Meaning |
|---|---|
| **Observed** | Read directly from data |
| **Modeled** | Output of the trained, evaluated classifier |
| **Derived** | Transparent arithmetic on observed/modeled values — no model |
| **Synthetic / prototype assumption** | A disclosed benchmark or evidence-readiness heuristic |

Details: [`docs/architecture/ai_orchestrator.md`](docs/architecture/ai_orchestrator.md).

---

## 11. Limitations

- **Fully synthetic benchmark.** No real Razorpay data, real merchant
  transactions, or real dispute outcomes anywhere in this project.
- **No claim to Razorpay's proprietary systems, data, or infrastructure.**
- **The current model is a provisional benchmark candidate** (Random
  Forest, 30-day horizon) — not a production deployment claim.
- **Intervention Intelligence is bounded and deterministic**, not a
  learned causal-optimization policy.
- **Risk Memory does not self-learn.** Every record's outcome is
  `not_observed` — there is no real post-intervention outcome data for
  it to learn from.
- **Simulator output is a bounded counterfactual model result**
  ("MODELED IMPACT"), never a causal guarantee.

Full, itemized limitations and failure analysis:
[`EVALUATION.md`](EVALUATION.md).

---

## 12. Documentation Map

| Document | Covers |
|---|---|
| [`PRODUCT.md`](PRODUCT.md) | Product behavior and scope |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture |
| [`EVALUATION.md`](EVALUATION.md) | Quantitative evaluation and failure analysis |
| [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) | Research journey and evidence |
| [`SECURITY.md`](SECURITY.md) | Security / data-handling notes |

---

## 13. Project Status

The core Sentinel product — risk engine, explainability, exposure/
liquidity, simulator, intervention intelligence, incident response,
evidence readiness, AI orchestrator, and Risk Memory V1 — is
substantially implemented and evaluated, across all six dashboard
screens (Overview, Risk, Explainability, Simulator, Incident Response,
Evidence).

**Remaining work** is presentation and delivery, not core product
scope:

- 3D marketing website
- 3D Research Lab (a section inside that marketing website)
- Final deployment
- Pitch / demo video

None of the above are complete yet — see [Links / Demo](#14-links--demo).

---

## 14. Links / Demo

| | |
|---|---|
| **Live Product** | *placeholder — to be added after deployment* |
| **3D Marketing Website** | *placeholder — not yet built* |
| **Pitch / Demo Video** | *placeholder — not yet recorded* |
| **GitHub Repository** | this repository |
