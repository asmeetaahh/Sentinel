<div align="center">

# Sentinel

**Sentinel helps merchants see an emerging chargeback-risk episode before it becomes a financial surprise.**

*Merchant-facing AI Risk Manager — independent product prototype, Razorpay Buildathon Track 02*

[Live Product](#) · [3D Marketing Website](#) · [Pitch / Demo Video](#) · [Research Journey](docs/research/RESEARCH.md)

</div>

---

## 1. What Sentinel Is

Sentinel is a **merchant-facing risk-intelligence product**: it detects
when a merchant's chargeback-loss exposure is becoming materially
elevated, explains why in plain, verifiable terms, translates that risk
into cash-flow and liquidity consequences, lets the merchant test
bounded operational changes before committing to one, and prepares them
to respond if the risk actually turns into an incident.

It is a working system, not a slide deck — a typed backend, a
six-screen dashboard, and a grounded AI layer, all runnable today. Its
underlying risk model is currently built and evaluated on a synthetic
benchmark (see [§9](#9-evidence-and-evaluation)), and it makes no claim to
Razorpay's proprietary data, risk systems, or dispute infrastructure.

---

## 2. The Real Merchant Problem

A merchant does not experience risk as an isolated model score. They
experience it as **rising disputes, potential loss exposure,
operational pressure, settlement and working-capital uncertainty**, and
the harder question underneath all of it: *what should I actually do
about this before it gets worse?*

Most of that experience is retrospective. A merchant typically finds
out their risk was elevated only once chargebacks have already landed
— at which point the loss is no longer a forecast, it is a fact. The
financial-continuity pressure this creates (will this month's exposure
eat into available liquidity, is there time to act, is the business
prepared to respond) is a real operational problem for a merchant, even
though no part of it requires — and Sentinel does not claim — visibility
into a payment platform's internal settlement, enforcement, or bank
decisions. It is a problem about the merchant's own trailing operational
signals and how early those signals can be turned into something
actionable.

---

## 3. The Gap Sentinel Fills

Existing payment-risk infrastructure is real and mature, but it mostly
sits at two different points in time relative to a merchant's own risk
trend:

```
TRANSACTION DECISIONING          →  approve/decline a single payment, at authorization time
DISPUTE PREVENTION / RESPONSE    →  intercept or respond to a dispute once one already exists
```

Between those two points is a layer that most infrastructure does not
occupy: a **merchant-level, forward-looking decision layer** that looks
at a merchant's own trailing behavior over time — not a single payment —
and asks whether it is heading somewhere bad early enough to matter.
Sentinel is built specifically for that layer:

```
merchant-level risk exposure → explanation → financial translation
    → bounded what-if simulation → intervention guidance → incident/evidence readiness
```

This "layer in between" is the central idea behind the product: not a
better transaction score, and not a faster dispute-response tool, but
the connective layer that turns an early signal into something a
merchant can actually reason about and act on.

---

## 4. What the Product Actually Does

These are not independent features bolted together — each stage exists
because the one before it, on its own, is not enough to be useful. A
risk score without an explanation isn't trustworthy. An explanation
without a financial translation isn't actionable. A translation without
a way to test a response isn't a decision tool. Sentinel is the chain
that connects all of them:

| Stage | What it does | Status |
|---|---|---|
| **Risk detection** | Flags materially elevated 30-day chargeback-loss exposure for a merchant | **Implemented** |
| **Explainability** | SHAP-based, faithfulness-verified drivers behind that score | **Implemented** |
| **Exposure / Liquidity translation** | Converts modeled risk into an exposure figure and a liquidity-stress ratio | **Implemented** (transparent derivation, not a second model) |
| **What-if simulator** | Bounded, deterministic counterfactuals over 3 real operational controls | **Implemented** |
| **Intervention Intelligence** | Grounded, ranked suggestions for what to test, tied to observed deviation + SHAP | **Implemented** |
| **Incident Response** | Turns a detected episode into reason code, priority, and a response-prep workflow | **Implemented** |
| **Evidence Readiness** | Reports what evidence is available vs. missing for a detected incident | **Implemented** |
| **AI Orchestrator** | A grounded assistant that explains the above in natural language | **Implemented** |
| **Risk Memory** | Records intervention/simulation activity for the session | **Implemented as scaffolding** — in-process, not persisted, cleared on every backend restart |
| **Outcome learning loop** | Learning which interventions actually work from real outcomes | **Not built** — see [§10](#10-research-journey-as-supporting-evidence) |

Full behavior and scope: [`PRODUCT.md`](PRODUCT.md).

---

## 5. What Makes Sentinel Different

Sentinel is not trying to replace a payment processor, a transaction
fraud engine, a chargeback-guarantee product, or a dispute-management
platform. Those solve real, different problems at different points in
the timeline. Sentinel's distinctive focus is the decision layer above
all of them:

- **Merchant-level and forward-looking**, not transaction-level — it
  reasons about a merchant's trailing operational trend, not whether to
  approve one payment.
- **Risk translated into financial-continuity terms**, not left as an
  abstract probability — exposure and liquidity-stress figures a
  merchant can actually reason about.
- **Explainability with real provenance**, not a black box — every
  number is labeled observed, modeled, or derived, and every SHAP
  explanation is checked to reconstruct the model's own output before
  it's ever shown.
- **Bounded counterfactual simulation** that turns a score into a
  decision tool — "what if I changed this" — without pretending to be a
  causal guarantee.
- **Intervention Intelligence** that connects a detected signal to a
  concrete, testable operational lever, not just a recommendation with
  no next step.
- **An outcome-recording foundation (Risk Memory)**, honestly scoped —
  it records what was tried and precisely, explicitly, does not claim
  to have learned from outcomes that don't yet exist in this benchmark.
- **Incident and evidence readiness treated as the same intelligence
  chain that detected the risk**, not a bolted-on ticketing feature.
- **A grounded AI layer** that explains already-computed product
  outputs — it does not calculate risk itself, and every number it
  cites is verified identical to the same authoritative service every
  dashboard screen uses.
- **Explicit uncertainty everywhere** — synthetic-data boundaries,
  model limitations, and unresolved findings are shown in the product,
  not hidden behind polish.

The prototype combines these capabilities into one connected workflow
rather than shipping any single one as an isolated feature — that
combination, not any one piece alone, is the product thesis.

---

## 6. Why This Matters to Razorpay / Business Value

This section describes **potential strategic value**, not a demonstrated
outcome. The current prototype demonstrates that this kind of
merchant-level decision layer can be built end-to-end and evaluated
honestly on a synthetic benchmark — it does **not** demonstrate reduced
chargebacks, reduced churn, reduced support costs, or reduced losses for
any real merchant or for Razorpay, and no claim to that effect is made
anywhere in this repository.

If a capability like this were built and validated on real merchant
data inside a payment platform, the strategic opportunity it points
toward includes:

- Helping merchants identify deteriorating operational risk earlier
  than a purely retrospective view allows.
- Making a complex risk signal understandable — drivers, financial
  consequence, and next steps — instead of a single opaque score.
- Helping merchants decide **what is worth testing operationally**
  before committing to a change, rather than guessing.
- Potentially reducing avoidable loss and improving merchant resilience
  — a hypothesis this prototype is built to eventually test, not a
  result it has produced.
- Making a payment platform more valuable to merchants beyond raw
  transaction processing, by adding a decision-support layer merchants
  don't otherwise get.
- Creating room for premium risk-intelligence or merchant-tooling
  products built on top of the same underlying signals.
- Longer-term, informing merchant financial-health or working-capital
  products — strictly contingent on real-data validation this prototype
  has not performed.

**What would be required to validate any of this**: real merchant
transaction and outcome data, a real deployment, and a real evaluation
of whether interventions merchants actually took changed their
real-world risk — none of which exists in this repository today (see
[§10](#10-research-journey-as-supporting-evidence) and
[§11](#11-limitations--honest-boundaries)).

---

## 7. How the Technical System Makes This Credible

Before the specific numbers ([§9](#9-evidence-and-evaluation)), the short
version of why this isn't a hand-waved concept: the risk model was
built on a **reproducible synthetic benchmark** (fixed seed, byte-
identical regeneration), evaluated with a **held-out, merchant-level
test split** and a **separate temporal stress test** on a later,
never-trained-on time period, compared against real baselines (not just
reported in isolation), and explained with SHAP attributions that are
checked — not assumed — to reconstruct the model's own output. The
product sits on a **typed FastAPI backend** and a **React dashboard**
that render only what the API actually returns, with a **grounded AI
layer** that cites verified numbers rather than generating its own, and
an **automated test suite** (563 tests across backend, ML, and frontend)
that exercises this behavior directly rather than by inspection.

This is engineering rigor in service of the product story — the next
two sections show what that rigor actually is (§8) and what it actually
found, including where it didn't work (§9).

---

## 8. Product Workflow / Architecture

**The product loop:**

```
Observe → Predict → Explain → Translate → Simulate → Decide → Prepare
```

- **Observe** — a merchant's own trailing operational behavior: refund
  rate, on-time fulfillment, chargeback history, customer mix, GMV.
- **Predict** — the saved 30-day model flags materially elevated
  chargeback-loss exposure against its own decision threshold.
- **Explain** — SHAP attributions show which observed signals pushed
  that score up or down, verified to reconstruct the model's own output.
- **Translate** — the modeled risk becomes an exposure figure and a
  liquidity-stress ratio, in terms a merchant can act on.
- **Simulate** — a bounded what-if tool re-runs the same model under a
  merchant-adjusted control and reports a **MODELED IMPACT**, never a
  guarantee.
- **Decide** — Intervention Intelligence surfaces which of those
  controls is actually worth testing, grounded in observed deviation
  and SHAP corroboration.
- **Prepare** — if risk becomes an incident, response preparation and
  evidence readiness connect prevention to response.

**System architecture:**

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

## 9. Evidence and Evaluation

All results below are measured on a **fully synthetic, reproducible
benchmark**: 50 merchants × 180 days, one fixed seed, 8 merchant
archetypes, 140 scheduled scenario events, 55 engineered features. No
real Razorpay or merchant data is used anywhere in this repository.
Both favorable and unfavorable findings are reported — nothing here is
cherry-picked:

| Result | Value |
|---|---|
| PR-AUC, Random Forest, 7d / 14d / 30d | 0.262 / 0.370 / 0.603 |
| PR-AUC, 30d, temporal stress test (later, unseen period) | 0.603 → **0.476** |
| Median warning lead time, 30d (after a measurement bug fix) | **7.0 days** |
| Brier score, uncalibrated vs. calibrated (30d) | 0.188 → **0.192 (no improvement)** |
| Hard-negative (growth ≠ risk) behavior | Holds in aggregate; **fails on one scenario type** (100% false-positive rate, small sample) |
| Exposure regression vs. a trailing-average baseline | **Beaten by the simpler baseline** — no regression artifact shipped |
| Incident detection (real episodes the model actually flagged) | 50 of 80 injected risk episodes, across 34 of 50 merchants |

Predictive separation increases materially with horizon; 7-day
prediction remains weak, so the product does not present a 7-day
prediction as a reliable warning. The selected candidate degrades under
temporal drift rather than surviving it cleanly. Calibration and
exposure regression are reported as **negative results**, not hidden —
investigating them honestly, and shipping the simpler, defensible
option instead of the more impressive-looking one, is itself part of
the credibility case, not a footnote.

**This is synthetic-benchmark evidence. It does not establish
production performance, real-merchant validity, or causal effect of any
intervention or simulator output.** Full methodology, every metric, and
the complete failure analysis: [`EVALUATION.md`](EVALUATION.md).

---

## 10. Research Journey as Supporting Evidence

Research is the evidence layer behind the product, not the product's
identity. Before writing product code, the underlying thesis — that a
merchant-level, forward-looking signal is worth building at all — was
deliberately stress-tested rather than assumed:

```
Question → Landscape → Candidate Gaps → Falsification → Hypothesis
    → Experiment → Results → Failure Analysis → Intervention → Future
```

That includes a chapter dedicated to actively trying to falsify the
product thesis before committing to it (would a simpler dispute-
prevention tool make this unnecessary? would a chargeback guarantee be
more valuable to a merchant than prediction? could the model just be
mistaking healthy growth for risk?) and an honest account of what
survived that scrutiny and what didn't. The full narrative is documented
in [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) — it is not
reproduced here, and it is intentionally positioned as validation
*behind* the product, not as a separate research project this repository
happens to also contain.

---

## 11. Limitations / Honest Boundaries

- **Fully synthetic benchmark.** No real Razorpay data, real merchant
  transactions, or real dispute outcomes anywhere in this project.
- **No claim to Razorpay's proprietary systems, data, or
  infrastructure** — including no claim to predict Razorpay's internal
  settlement-hold decisions, enforcement actions, internal risk scores,
  or bank decisions. Sentinel models only observable, synthetic
  merchant-level signals.
- **The current model is a provisional benchmark candidate** (Random
  Forest, 30-day horizon) — not a production deployment claim.
- **Intervention Intelligence is bounded and deterministic**, not a
  learned causal-optimization policy.
- **Risk Memory does not self-learn and is not persistent.** It is an
  in-process, session-scoped record, cleared on every backend restart;
  every outcome is `not_observed` — there is no real post-intervention
  outcome data for it to learn from.
- **Simulator output is a bounded counterfactual model result**
  ("MODELED IMPACT"), never a causal guarantee.
- **No real-world performance validation.** Every metric in this
  repository comes from the synthetic benchmark described in §9.

Full, itemized limitations, failure analysis, and security posture:
[`EVALUATION.md`](EVALUATION.md) and [`SECURITY.md`](SECURITY.md).

---

## 12. Links

| | |
|---|---|
| **Live Product** | *placeholder — to be added after deployment* |
| **3D Marketing Website** | *placeholder — not yet built (will include the 3D Research Lab as a supporting exploration of the evidence behind Sentinel, not as Sentinel's primary identity)* |
| **Pitch / Demo Video** | *placeholder — not yet recorded* |
| **Research Journey** | [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) |
| **GitHub Repository** | this repository |

---
---

# Appendix: Repository Reference

The sections below are practical reference material — repository
layout, how to run Sentinel locally, and the technology stack — kept
after the product narrative above so a reader gets the product case
first and the operational detail second.

## Repository Structure

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

## Running Sentinel Locally

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

macOS also requires `brew install libomp` for XGBoost (training/
evaluation scripts only, not the served backend — see `requirements.txt`).

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

## Technology

- **Backend**: Python, FastAPI, Pydantic v2, uvicorn — typed, read-only
  API over the trained model and benchmark artifacts.
- **ML**: numpy, pandas, scikit-learn, XGBoost, SHAP.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, recharts,
  react-router-dom.
- **Testing**: pytest (backend/ML), Vitest + Testing Library (frontend).
- **AI providers**: a deterministic mock provider (default, no network
  dependency); OpenAI; Featherless.ai (OpenAI-compatible, open-weight
  models) — both real providers optional and lazily loaded.

No database and no auth layer exist — the backend serves a fixed,
local, synthetic dataset read-only from disk.

## AI / Assistant Honesty

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

## Documentation Map

| Document | Covers |
|---|---|
| [`PRODUCT.md`](PRODUCT.md) | Product behavior and scope |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture |
| [`EVALUATION.md`](EVALUATION.md) | Quantitative evaluation and failure analysis |
| [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md) | Research journey and evidence |
| [`SECURITY.md`](SECURITY.md) | Security / data-handling notes |

## Project Status

The core Sentinel product — risk engine, explainability, exposure/
liquidity, simulator, intervention intelligence, incident response,
evidence readiness, AI orchestrator, and Risk Memory V1 — is
substantially implemented and evaluated, across all six dashboard
screens (Overview, Risk, Explainability, Simulator, Incident Response,
Evidence).

**Remaining work** is presentation and delivery, not core product
scope:

- 3D marketing website (including the 3D Research Lab section)
- Final deployment
- Pitch / demo video

None of the above are complete yet — see [§12](#12-links).
