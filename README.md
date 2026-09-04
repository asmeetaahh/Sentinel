<div align="center">

# Sentinel

**Sentinel helps a merchant see an emerging chargeback-risk episode before it becomes a financial surprise.**

*Merchant-facing AI Risk Manager — independent product prototype, Razorpay Buildathon Track 02*

</div>

---

## 1. What Sentinel Is

Sentinel is a merchant-facing risk-intelligence product. It detects when a merchant's chargeback-loss exposure is becoming materially elevated, explains why in plain and verifiable terms, translates that risk into cash-flow and liquidity consequences, lets the merchant test a bounded operational change before committing to one, and prepares them to respond if the risk turns into an incident.

It is a working system, not a slide deck: a typed FastAPI backend, a six-screen React dashboard, a separate marketing site, and a grounded AI layer, all runnable today. The underlying risk model is currently built and evaluated on a synthetic benchmark (see [§7](#7-held-out-evaluation)), and Sentinel makes no claim to Razorpay's proprietary data, risk systems, or dispute infrastructure.

---

## 2. Explore Sentinel

| | |
|---|---|
| **Live Product** | [sentinel-dashboard-39tw.onrender.com](https://sentinel-dashboard-39tw.onrender.com/) |
| **Marketing Site** | [sentinel-marketing-suzb.onrender.com](https://sentinel-marketing-suzb.onrender.com/) |
| **Demo Video** | [Watch on Google Drive](https://drive.google.com/file/d/10x-h0YaBS_qooRwld6pYcPI3_abHHYTw/view?usp=sharing) |
| **Research Journey** | [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) |
| **GitHub Repository** | [github.com/asmeetaahh/Sentinel](https://github.com/asmeetaahh/Sentinel) |

---

## 3. The Problem Sentinel Solves

A merchant does not experience risk as an isolated model score. They experience it as rising disputes, potential loss exposure, operational pressure, and settlement or working-capital uncertainty, underneath one harder question: *what should I actually do about this before it gets worse?*

Most of that experience is retrospective today. A merchant typically learns their risk was elevated only after chargebacks have already landed, at which point the loss is a fact, not a forecast. That is a real problem about a merchant's own trailing operational signals and how early they can be turned into something actionable — it does not require, and Sentinel does not claim, visibility into a payment platform's internal settlement, enforcement, or bank decisions.

Existing payment-risk infrastructure sits at two other points in time relative to a merchant's own risk trend:

```
TRANSACTION DECISIONING          →  approve/decline a single payment, at authorization time
DISPUTE PREVENTION / RESPONSE    →  intercept or respond to a dispute once one already exists
```

Sentinel is built for the layer in between: a merchant-level, forward-looking decision layer that looks at a merchant's own trailing behavior over time, not a single payment, and asks whether it is heading somewhere bad early enough to matter.

---

## 4. Why Sentinel Is Different

Sentinel is not trying to replace a payment processor, a transaction fraud engine, a chargeback-guarantee product, or a dispute-management platform. Those solve real problems at different points in the timeline. Sentinel's focus is the decision layer above all of them:

- **Merchant-level and forward-looking**, not transaction-level — it reasons about a merchant's trailing operational trend, not whether to approve one payment.
- **Risk translated into financial-continuity terms**, not left as an abstract probability — an exposure figure and a liquidity-stress ratio a merchant can reason about.
- **Explainability with real provenance**, not a black box — every number is labeled observed, modeled, or derived, and every SHAP explanation is checked to reconstruct the model's own output before it is shown.
- **Bounded counterfactual simulation** that turns a score into a decision tool ("what if I changed this") without pretending to be a causal guarantee.
- **Intervention Intelligence** that connects a detected signal to a concrete, testable operational lever, not just a recommendation with no next step.
- **An outcome-recording foundation (Risk Memory)**, honestly scoped — it records what was tried and explicitly does not claim to have learned from outcomes that don't yet exist in this benchmark.
- **Incident and evidence readiness** treated as part of the same intelligence chain that detected the risk, not a bolted-on ticketing feature.
- **A grounded AI layer** that explains already-computed product outputs. It does not calculate risk itself, and every number it cites is verified identical to the same authoritative service every dashboard screen uses.
- **Explicit uncertainty everywhere** — synthetic-data boundaries, model limitations, and unresolved findings are shown in the product, not hidden behind polish.

The combination of these pieces into one connected workflow, not any single one alone, is the product thesis.

---

## 5. Product Workflow

```
Observe → Predict → Explain → Translate → Simulate → Decide → Prepare
```

- **Observe** — a merchant's own trailing operational behavior: refund rate, on-time fulfillment, chargeback history, customer mix, GMV.
- **Predict** — the saved 30-day model flags materially elevated chargeback-loss exposure against its own decision threshold.
- **Explain** — SHAP attributions show which observed signals pushed that score up or down, verified to reconstruct the model's own output.
- **Translate** — the modeled risk becomes an exposure figure and a liquidity-stress ratio, in terms a merchant can act on.
- **Simulate** — a bounded what-if tool re-runs the same model under a merchant-adjusted control and reports a **MODELED IMPACT**, never a guarantee.
- **Decide** — Intervention Intelligence surfaces which of those controls is actually worth testing, grounded in observed deviation and SHAP corroboration.
- **Prepare** — if risk becomes an incident, response preparation and evidence readiness connect prevention to response.

---

## 6. Product Overview

Six connected dashboard screens carry this loop end to end. A live walkthrough is in the [demo video](#2-explore-sentinel); this table is the quick reference:

| Screen | What it shows |
|---|---|
| **Overview** | Current risk state (Normal/Elevated), 30-day modeled probability, confidence/data-quality indicator, 90-day trend of observed GMV/chargeback/refund rate |
| **Risk** | The full modeled risk read for a merchant, with the same provenance labeling used everywhere else |
| **Explainability** | SHAP-based drivers behind the score, faithfulness-verified against the model's own output |
| **Simulator** | Bounded what-if controls (refund rate, on-time fulfillment, new-customer share) and the resulting MODELED IMPACT |
| **Incident Response** | Detected episodes, reason code, priority, and a four-step response-preparation tracker |
| **Evidence** | Per-incident evidence readiness across seven categories, each resolved by a disclosed rule |

Every stage exists because the one before it, on its own, is not enough to be useful: a risk score without an explanation isn't trustworthy, an explanation without a financial translation isn't actionable, and a translation without a way to test a response isn't a decision tool.

| Stage | Status |
|---|---|
| Risk detection, explainability, exposure/liquidity translation | Implemented |
| What-if simulator, Intervention Intelligence | Implemented |
| Incident response, evidence readiness | Implemented |
| AI orchestrator (grounded, provenance-labeled) | Implemented |
| Risk Memory | Implemented as scaffolding — in-process, not persisted, cleared on every backend restart |
| Outcome-learning loop (learning which interventions work from real outcomes) | Not built — see [§9](#9-what-we-learned--failure-analysis) |

Full behavior and scope: [`PRODUCT.md`](PRODUCT.md).

---

## 7. Held-Out Evaluation

All results below are measured on a fully synthetic, reproducible benchmark and cross-checked directly against the committed evaluation artifacts (`data/metadata/modeling/results.json`, `calibration_results.json`). No real Razorpay or merchant data is used anywhere in this repository.

**Selected candidate: Random Forest, 30-day horizon, held-out merchant-level test set (n = 960 rows, 8 merchants never seen in training):**

| Metric | Value |
|---|---|
| Precision | 0.502 |
| Recall | 0.552 |
| F1 | 0.526 |
| PR-AUC | 0.603 |
| Confusion matrix (TN / FP / FN / TP) | 587 / 132 / 108 / 133 |
| Median warning lead time | 7.0 days |
| Brier score (uncalibrated) | 0.188 |
| Brier score (calibrated, sigmoid) | 0.192 — no improvement |
| Incidents actually flagged | 50 of 80 injected risk episodes, across 34 of 50 merchants |

**Temporal stress test** (same 8 test merchants, evaluated only on a later time window the model never trained on):

| Horizon | Normal PR-AUC | Stress PR-AUC | Δ |
|---|---|---|---|
| 30 days | 0.603 | **0.476** | −0.127 (−21% relative) |

Random Forest at 30 days still clearly beats the baseline and stays well above chance, but this is a real, non-trivial sensitivity to distribution shift, not a clean survival.

Full methodology, every metric, and the complete failure analysis: [`EVALUATION.md`](EVALUATION.md).

---

## 8. Baseline Comparison

Four models were evaluated unconditionally across three horizons, with hyperparameters fixed before any test-set result was seen:

| Model | Horizon | Precision | Recall | F1 | PR-AUC |
|---|---|---|---|---|---|
| Historical-threshold baseline | 30d | 0.252 | 1.000 | 0.402 | 0.257 |
| Logistic Regression | 30d | 0.455 | 0.718 | 0.557 | 0.486 |
| **Random Forest** | **30d** | **0.502** | 0.552 | 0.526 | **0.603** |
| XGBoost | 30d | 0.437 | 0.751 | 0.553 | 0.467 |

The historical-threshold baseline's near-perfect recall is not skill: at 30 days it flags 997 of 1,000 test rows positive, close to a "flag-everything" strategy, and its PR-AUC (0.257) sits barely above the raw positive rate. Random Forest was selected for the best PR-AUC at the strongest horizon and the best false-positive profile of the four (132 FP vs. 133 TP, the only model with FP:TP under 1 at 30 days) — not a clean win, since XGBoost and Logistic Regression are close on F1 and Random Forest shows the largest degradation of the three under temporal stress.

PR-AUC across horizons for every real model:

| Model | 7d | 14d | 30d |
|---|---|---|---|
| Logistic Regression | 0.226 | 0.301 | 0.486 |
| Random Forest | 0.262 | 0.370 | 0.603 |
| XGBoost | 0.221 | 0.269 | 0.467 |

---

## 9. What We Learned / Failure Analysis

Both favorable and unfavorable findings are reported here. Nothing in this section is cherry-picked.

- **7-day prediction is weak.** PR-AUC at 7 days (0.221–0.262 across models) adds little over chance-ranking. Sentinel does not present a 7-day prediction as a reliable warning.
- **30 days is the strongest evaluated horizon.** Predictive separation rises sharply and consistently with horizon for every real model, at a rate that outpaces the modest rise in positive-class base rate — a genuine horizon effect, not just "more positives = easier."
- **Temporal stress degrades PR-AUC.** The selected 30-day candidate drops from 0.603 to 0.476 (−21% relative) on a later, never-trained-on period of the same held-out merchants. It survives partially, not cleanly.
- **Calibration did not improve Brier score.** A Platt (sigmoid) calibration layer was fit and evaluated; Brier score went from 0.188 to 0.192 (worse), and worse still under temporal stress (0.231 → 0.253). Precision/recall/F1/PR-AUC are mathematically unchanged by construction (sigmoid scaling is monotonic). Both variants ship; neither is presented as "calibrated and ready."
- **Exposure regression lost to a simpler baseline.** A Random Forest regression candidate for future chargeback amount was beaten on MAE and RMSE by a naive trailing-average persistence baseline at 14d and 30d. No regression artifact was ever shipped — the product's exposure figure uses the same trailing-average baseline directly, labeled `derived`.
- **A hard-negative scenario failed.** The benchmark's central design constraint (growth ≠ risk) holds in aggregate, but the `viral_campaign` hard-negative scenario shows a 100% false-positive rate (n = 7, a small sample) — exactly the failure mode this part of the benchmark exists to expose. `payment_method_shift`, another hard-negative type, holds cleanly at a 0% false-positive rate.
- **A warning lead-time measurement bug was found and fixed.** The first implementation credited Random Forest at 30d a median lead time of 30.0 days — indistinguishable from "always fires" — because it did not require the positive prediction to be contiguous with the episode's onset. The corrected, honest figure is 7.0 days.
- **An archetype was structurally suppressed by a generator bug, and corrected.** The Education archetype's original transaction-volume parameters made chargeback outcomes nearly unobservable regardless of injected risk severity, not a genuine "low-risk" finding. Fixing the volume parameters (not the risk-rate parameters) moved Education from the lowest positive-rate archetype to mid-pack.
- **An unresolved SHAP finding remains open.** In two individually inspected high-confidence positive predictions, a chargeback-rate feature value of exactly 0.0 pushed the score *up*, opposite to that feature's global average signed direction. This is not a contradiction (SHAP can capture real interaction effects), but it has not been root-caused.

Full failure analysis, including every corrected bug and every negative result: [`EVALUATION.md` §17](EVALUATION.md).

---

## 10. Architecture and the AI Boundary

**System flow:**

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

The central architectural principle: **the system that computes risk remains structurally separate from the system that explains it.** The AI layer never writes into a risk, exposure, liquidity, SHAP, simulation, or incident value.

**The AI boundary, specifically:**

- Every number the AI orchestrator discusses is computed by an existing backend service before the AI provider is ever called, and a dedicated test independently verifies the assistant's cited numbers are byte-identical to the same authoritative service call every dashboard screen makes.
- A deterministic pre-filter checks every incoming question for known prompt-injection phrasings before any provider is called; a second, prompt-level instruction treats the user's own message as untrusted input.
- The default provider is a fully deterministic mock (no network calls). Two real providers — OpenAI and an OpenAI-compatible open-weight provider (Featherless.ai) — are supported and always labeled with the exact provider/model identifier that produced a response, never presented as though the model itself performed the risk analysis.

Every value Sentinel shows is labeled by provenance:

| Label | Meaning |
|---|---|
| **Observed** | Read directly from data |
| **Modeled** | Output of the trained, evaluated classifier |
| **Derived** | Transparent arithmetic on observed/modeled values — no model |
| **Synthetic / prototype assumption** | A disclosed benchmark or evidence-readiness heuristic |

Full implementation-level design: [`ARCHITECTURE.md`](ARCHITECTURE.md). AI orchestrator detail: [`docs/architecture/ai_orchestrator.md`](docs/architecture/ai_orchestrator.md).

---

## 11. Synthetic Benchmark Methodology

- **Scale**: 50 merchants × 180 days, one fixed seed (42), 9,000 daily rows, zero date gaps, zero duplicate rows, zero nulls.
- **Archetypes**: 8 merchant archetypes (D2C Fashion, Electronics, SaaS, Travel, Marketplace, Education, Quick Commerce, Digital Goods), each with its own baseline ranges for GMV, AOV, refund/chargeback rates, fulfillment speed, and payment mix.
- **Events**: 140 scheduled scenario events across 9 types — 5 risk types and 4 benign-growth hard negatives — using a smoothstep onset/decay ramp with no same-merchant overlap.
- **Features**: 55 engineered features across 9 groups, all causal (a trailing or expanding window ending at the prediction date). The feature pipeline never imports the events or labels files at all.
- **Split**: merchant-level, archetype-stratified (64.0% train / 20.0% validation / 16.0% test); no merchant appears in more than one split.
- **Temporal cutoff**: `day_index < 120` for training and the normal test; `day_index >= 120`, only on the already-held-out test merchants, for the temporal stress test.
- **Leakage controls**: a column-name audit, a ground-truth-leakage check, a single-feature AUC audit, and a feature-importance-concentration check all pass at every horizon. Truncation invariance is proven directly: generating only the first 60 days of a run reproduces byte-identical output to the first 60 days of a 120-day run with the same seed.
- **Reproducibility**: regenerating seed 42 twice produces byte-identical CSVs; every random draw traces back to a keyed `numpy.random.SeedSequence`.

Full dataset methodology, every disclosed modeling assumption, and the dataset validation report: [`EVALUATION.md` §2–3](EVALUATION.md) and [`docs/research/dataset_validation_report.md`](docs/research/dataset_validation_report.md).

---

## 12. Limitations — What Sentinel Cannot Claim

- **Fully synthetic benchmark.** No real Razorpay data, real merchant transactions, or real dispute outcomes anywhere in this project. Every metric in this repository comes from the 50×180 synthetic benchmark described in [§11](#11-synthetic-benchmark-methodology).
- **No claim to Razorpay's proprietary systems, data, or infrastructure** — including no claim to predict or access Razorpay's internal settlement-hold decisions, enforcement actions, internal risk scores, or bank decisions. Sentinel models only observable, synthetic merchant-level signals.
- **The simulator is a modeled, counterfactual result, never a causal one.** It re-runs the same trained classifier under a bounded, merchant-adjusted input and reports a MODELED IMPACT — not a guarantee, and not an estimate of real-world causal effect.
- **Risk Memory is session-scoped and in-process, not an outcome-learning system.** It is cleared on every backend restart, is never written to disk, and every record's `outcome_status` is a hardcoded `not_observed` — there is no real post-intervention outcome data for it to learn from, and no code path can set it to anything else.
- **The current model is a provisional benchmark candidate** (Random Forest, 30-day horizon), not a production deployment claim.
- **Intervention Intelligence is bounded and deterministic**, not a learned causal-optimization policy.
- **No real-world performance validation.** Benchmark performance must not be read as production validation or a claim about real-world predictive accuracy.

Full, itemized limitations and security posture: [`EVALUATION.md`](EVALUATION.md) and [`SECURITY.md`](SECURITY.md).

---

## 13. Tech Stack

- **Backend**: Python, FastAPI, Pydantic v2, uvicorn — a typed, read-only API over the trained model and benchmark artifacts. No database, no auth layer; the backend serves a fixed, local, synthetic dataset read-only from disk.
- **ML**: numpy, pandas, scikit-learn, XGBoost, SHAP.
- **Dashboard** (`apps/dashboard`): React 19, TypeScript, Vite, Tailwind CSS v4, recharts, react-router-dom.
- **Marketing site** (`apps/marketing`): React 19, TypeScript, Vite, Tailwind CSS v4, GSAP + ScrollTrigger, Lenis — a cinematic, scroll-driven presentation layer built with layered CSS/SVG composition, not a 3D engine.
- **Testing**: pytest (backend/ML), Vitest + Testing Library (dashboard).
- **AI providers**: a deterministic mock provider (default, no network dependency); OpenAI; Featherless.ai (OpenAI-compatible, open-weight models) — both real providers optional and lazily loaded.

---

## 14. Project Structure

```
sentinel/
├── apps/
│   ├── dashboard/       React + TypeScript product dashboard (6 screens)
│   └── marketing/       React + TypeScript marketing site (scroll-driven, GSAP)
├── backend/             FastAPI backend — risk, simulation, incidents,
│                         evidence, interventions, memory, AI orchestrator
├── data/                Generated synthetic benchmark, features, ML artifacts
├── docs/
│   ├── architecture/    Per-module implementation design docs
│   └── research/        Research journey + dataset/baseline reports
├── ml/                  Data generation, feature engineering, modeling,
│                         explainability, validation
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

## 15. Local Setup

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

macOS also requires `brew install libomp` for XGBoost (training/evaluation scripts only, not the served backend — see `requirements.txt`).

### Dashboard

```bash
cd apps/dashboard
cp .env.example .env        # VITE_API_BASE_URL — point this at the backend port above
npm install
npm run dev                  # http://localhost:5173 (or next free port)
```

### Marketing site

```bash
cd apps/marketing
npm install
npm run dev                  # http://localhost:5173 (or next free port)
```

### Checks

```bash
# Python (332 tests)
.venv/bin/python -m pytest tests/ -v

# Dashboard (238 tests, from apps/dashboard/)
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

See `.env.example` and `apps/dashboard/.env.example`. Never commit a real API key; both example files are gitignored placeholders.

---

## 16. Supporting Documentation

| Document | Covers |
|---|---|
| [`PRODUCT.md`](PRODUCT.md) | Product behavior and scope |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture |
| [`EVALUATION.md`](EVALUATION.md) | Quantitative evaluation and failure analysis |
| [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) | Research journey and evidence |
| [`SECURITY.md`](SECURITY.md) | Security / data-handling notes |
| [`docs/architecture/`](docs/architecture/) | Per-module implementation design docs |

Sentinel's automated test suite currently covers 570 tests (332 backend/ML via pytest, 238 frontend via Vitest), exercising this behavior directly rather than by inspection.

### Project status

The core Sentinel product — risk engine, explainability, exposure/liquidity, simulator, intervention intelligence, incident response, evidence readiness, AI orchestrator, and Risk Memory V1 — is substantially implemented and evaluated, across all six dashboard screens. The dashboard, the marketing site, and this documentation set are complete and deployed; remaining work before submission is limited to final QA rather than new product scope.
