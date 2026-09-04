# SENTINEL — PRODUCT

## 1. Product Overview

Sentinel is a merchant-facing risk intelligence platform designed to help
payment merchants identify materially elevated future chargeback-loss
exposure early, understand the observable drivers behind that risk,
translate exposure into liquidity and continuity implications, evaluate
bounded what-if scenarios, act on grounded intervention opportunities, and
prepare for an incident if the risk materializes.

Every number Sentinel shows is labeled by where it came from: **observed**
(read directly from data), **modeled** (the output of a trained,
synthetic-benchmark classifier), **derived** (computed transparently from
observed/modeled values, not by any model), or a disclosed **synthetic
benchmark** assumption. Sentinel does not claim access to Razorpay's
proprietary risk systems, enforcement systems, or dispute infrastructure,
and does not claim access to real merchant transaction data. Everything in
the current product is built and evaluated against a fully synthetic,
reproducible benchmark.

**Core product loop:**

```
Risk → Explain → Exposure → Liquidity → Simulate → Intervene → Incident → Evidence → AI → Memory
```

**Product philosophy:**

> See the risk. Understand it. Simulate what could change. Know what to
> act on. Prepare if it happens. Remember what happened next.

---

## 2. Problem

Chargeback risk is usually treated as a transaction-level scoring
problem: score a payment, allow or block it. That is a different problem
from the one a merchant actually lives with. A merchant does not
experience a single transaction score — they experience a *pattern*: is
my risk actually getting worse this month, why, what would that cost me
if it continues, what could I change about how I operate, and — if it's
already too late to prevent — am I ready to respond and can I learn
anything from what I tried.

Sentinel is built around that gap: the space between *detecting* that a
merchant's risk has crossed a meaningful threshold and *doing something
useful with that fact* — understanding why, quantifying the financial
consequence, testing a bounded change before committing to it, preparing
evidence and response material if an incident is already underway, and
eventually building a record of what was tried and (once real outcome
data exists) what happened next.

Sentinel is deliberately **merchant-level intelligence**, not a
transaction-level fraud-scoring system. It reasons about a merchant's
trailing operational state — refund behavior, fulfillment performance,
customer mix, chargeback history, liquidity position — over time, not
about whether any single payment should be approved.

---

## 3. Target User

The intended user is a merchant-side operator, risk lead, or finance
decision-maker who needs to understand emerging payment risk and its
operational and financial consequences — not a card-network analyst and
not an end consumer.

The questions this user is trying to answer:

- "Is my risk actually getting worse?"
- "Why?"
- "How much exposure could this create?"
- "What could this mean for available liquidity?"
- "What operational lever should I investigate?"
- "What happens if I change that lever?"
- "If the issue materializes, are we prepared?"
- "What happened after we acted?"

Sentinel has not validated a specific commercial customer segment (SMB
vs. enterprise, specific vertical, specific deal size) — the product is
built for the role and the questions above, not a narrowly defined buyer.

---

## 4. Product Principles

### 4.1 Evidence before explanation
Every explanation Sentinel gives is built from observable or
model-derived data, never from an unsupported assumption presented as
fact.

### 4.2 Provenance matters
Every risk-relevant value is explicitly tagged: observed, modeled,
derived, a disclosed synthetic-benchmark assumption, or AI-generated
prose. The product never lets these blur together.

### 4.3 No fabricated certainty
Sentinel does not invent confidence scores, outcomes, transaction
records, evidence documents, or real-world validation that does not
exist. Where something is unknown or not yet observed, the product says
so plainly.

### 4.4 AI does not independently determine risk
The AI layer explains and orchestrates around verified, already-computed
context. It never calculates, infers, overrides, or invents a
risk/exposure/liquidity/SHAP/simulation/incident number — every number
the assistant discusses was computed by an existing service before the
AI provider is ever called.

### 4.5 Simulation is bounded
The what-if simulator shows what the same trained classifier outputs
under a different, bounded input. It is a modeled counterfactual, not a
causal claim and not a guarantee of real-world impact.

### 4.6 Merchant-level perspective
Sentinel focuses on a merchant's operational and financial state over
time, not on scoring individual transactions, and does not present
itself as a replacement for transaction-level, card-network, or
payment-processor risk systems.

### 4.7 Honest limitations
Synthetic-data boundaries, benchmark limitations, model limitations
(including where the model degrades or is not well-calibrated), and
unobserved real-world outcomes remain visible in the product rather than
hidden behind polish.

---

## 5. Current Product Capabilities

### 5.1 Merchant Risk Overview
The Overview and Risk screens show a merchant's current modeled risk
state (Normal / Elevated) and modeled 30-day probability against the
model's own decision threshold, a compact confidence/data-quality
indicator (High / Medium / Limited — a transparency signal about how
much history backs the read, not a model-accuracy claim), the merchant's
archetype/tier context, and a 90-day trajectory of real observed GMV,
chargeback rate, and refund rate. All model output is labeled
`modeled`, with an explicit disclaimer that it is a synthetic-benchmark
output, not a validated real-world probability.

### 5.2 Risk Drivers / Explainability
A dedicated Explainability screen (and the Overview risk-drivers card)
shows SHAP-based, per-prediction attributions for the same saved
classifier: which observed features pushed this merchant's score up or
down, and by how much. Every explanation is verified to reconstruct the
model's own raw probability before it is shown — the product refuses to
display an explanation that fails that check. SHAP attributes the
model's output to its inputs; it does not establish that any feature
*causes* elevated risk, and the product's language reflects that
distinction throughout.

### 5.3 Exposure Intelligence
Sentinel translates modeled risk into an estimated chargeback exposure
amount: a trailing-average extrapolation over the merchant's own recent
chargeback amounts, projected across the horizon. This is labeled
`derived`, not a model prediction — a regression model was evaluated for
this purpose in research and did not outperform this simpler baseline,
so no regression artifact was ever put into the product. These are
modeled/derived quantities that illustrate potential exposure, not
guaranteed future losses.

### 5.4 Liquidity / Continuity Intelligence
The product shows a merchant's observed available liquidity alongside a
derived liquidity-stress ratio (exposure estimate ÷ available liquidity)
— a plain, transparent calculation, not a second model. Its purpose is
to translate payment risk into financial-continuity terms a merchant can
act on ("how much of my buffer would this consume"), not to predict a
merchant's actual bank balance or settlement ledger, which Sentinel has
no access to.

### 5.5 Simulator
A bounded, deterministic what-if tool. A merchant can adjust up to three
of their own trailing operational metrics — refund rate, on-time
fulfillment rate, and new-customer share — and see how the exact same
saved model responds, with the resulting exposure and liquidity-stress
view shown alongside the current state. Every result is labeled
**MODELED IMPACT**. Simulation is explicitly not causal inference and
not a guarantee of real-world impact; the simulator remains the sole
source of any modeled intervention-impact number in the product.

### 5.6 Intervention Intelligence
A deterministic, rule-based layer — not an ML prediction and not an
AI-generated recommendation — that flags when one of the simulator's
three controllable metrics is meaningfully unusual for a specific
merchant (a statistical deviation from that merchant's own recent
baseline), optionally corroborated by whether that same behavior area is
currently a verified SHAP contributor to the merchant's risk. The flow:

```
Observed deviation signal → grounded recommendation → "Test in Simulator" → simulator → modeled impact
```

Recommendations state plainly why they were surfaced and link directly
into the simulator; they are never presented as an autonomous decision
or a guarantee that acting on them changes real-world risk. On most
merchant-days, no control clears the bar, and the product shows an
honest empty state rather than manufacturing a recommendation.

### 5.7 Incident Response
When a merchant's risk episode was actually flagged by the same saved
model and threshold used elsewhere in the product, it becomes a
selectable incident: risk/exposure/liquidity/driver context at the
moment of detection, a disclosed prototype reason code, a transparent
priority (built from stated, inspectable reasons, never an opaque
score), and a four-step response-preparation tracker (Review → Evidence
check → Prepare response → Merchant confirmation required). This is the
transition from prevention to response inside Sentinel's core loop.
Preparing a response never submits anything anywhere — the product
states explicitly that nothing is filed and that any real submission
would go through Razorpay's actual dispute process, which Sentinel does
not have access to.

### 5.8 Evidence Readiness
For each incident, Sentinel reports which of seven evidence categories
(invoice, payment confirmation, delivery proof, tracking information,
refund confirmation, customer communication, service/access records)
are available versus missing, with the exact rule behind each
disclosed — some derived from observed fulfillment/refund data, some
explicitly labeled synthetic-benchmark assumptions. Sentinel does not
fabricate evidence: no invoice, tracking number, or message is ever
invented. Missing evidence stays reported as missing. Readiness is
reported at the aggregate incident level, using aggregate benchmark
observations — this is explicitly not a substitute for transaction-level
dispute records.

### 5.9 AI Orchestrator
A bounded assistant embedded on the Overview, Simulator, and Incident
Response screens. Its context is assembled exclusively from the same
already-computed, already-verified services every other screen uses —
risk, exposure, liquidity, drivers, simulation, incident, intervention
recommendations, and confidence/data-quality — never computed by the AI
itself. The flow:

```
Verified context → AI explanation/orchestration → grounded response
```

The assistant can explain already-computed risk, exposure, liquidity,
drivers, a simulation, an incident, evidence readiness, or an
intervention recommendation. It must not, and structurally cannot,
independently calculate a risk number, invent an unsupported fact,
fabricate evidence, claim a real-world outcome was observed, or claim
access to proprietary systems — enforced by a fixed system prompt, a
deterministic pre-filter against prompt injection, and a response schema
where every cited number is a direct pass-through of verified backend
state. A default, fully deterministic mock provider requires no network
access; two real LLM provider integrations (OpenAI, and an
OpenAI-compatible open-weight provider) are supported and clearly
labeled whenever active, never presented as though the model itself
performed the risk analysis.

### 5.10 Risk Memory / Outcome Loop
A lightweight, in-process record of intervention and simulation activity
per merchant, for the current session only:

```
Action → Simulation → Outcome
```

Because the current synthetic benchmark has no post-intervention data
collection, the real outcome of any recorded action is always reported
as **`outcome_status: not_observed`** — never fabricated, never inferred,
never converted from a simulated result into a claimed real one. This
establishes the architecture and data model an outcome-learning system
would need, without claiming Sentinel has learned anything from
interventions it cannot yet measure.

---

## 6. Research-Backed Product Foundation

Every product surface above sits on top of a research pipeline that was
built and evaluated before any of it was product-facing:

- A **reproducible synthetic benchmark** (fixed seed, deterministic
  generation) of merchant payment behavior across eight archetypes.
- **Explicit leakage controls** — features are computed causally
  (only information available at or before the prediction date), with
  structural checks that forbidden columns never enter the feature
  matrix or explanation layer.
- **Merchant-level train/validation/test splitting**, so no merchant
  appears in more than one split.
- **Deliberate hard negatives** — scenarios where GMV and volume rise
  substantially while chargeback/refund/fulfillment health stays normal,
  so the model is challenged to distinguish healthy growth from
  deteriorating operations rather than learning "growth equals risk."
- **Baseline-vs-candidate model comparison** across a historical
  threshold, logistic regression, Random Forest, and XGBoost, evaluated
  on precision, recall, F1, PR-AUC, and false-positive cost.
- **Temporal stress testing** against a later, never-trained-on period
  of the same held-out merchants, to check survival under distribution
  shift.
- **Warning lead-time analysis** as the signature evaluation metric —
  including a discovered and corrected measurement bug, documented
  rather than hidden.
- **Calibration investigation** for the selected candidate, with the
  finding reported honestly even where calibration did not clearly
  improve the model.
- **SHAP verification** — every explanation is checked to reconstruct
  the model's own output before being shown, not assumed correct.
- **Provenance separation** carried from the research pipeline all the
  way to the screen.
- **Honest failure analysis**, including known false-positive patterns
  and unresolved archetype-level disparities, documented rather than
  smoothed over.

These are the supporting research foundations that make the product
defensible — not separate user-facing features. Full methodology,
metrics, and findings live in the research documentation, not here.

---

## 7. What Sentinel Is NOT

Sentinel is **not**:

- A replacement for Razorpay's proprietary risk systems.
- A payment processor.
- A card-network risk engine.
- A transaction-level fraud-prevention system.
- An autonomous dispute-filing system.
- A source of real merchant transaction records.
- A causal inference engine.
- A guaranteed loss predictor.
- A lending or working-capital product today.
- An AI system that independently determines risk.
- A system with real intervention-outcome data in the current synthetic
  benchmark.

---

## 8. Product Boundaries & Trust Model

Sentinel makes a strict distinction between:

| Label | Meaning |
|---|---|
| **OBSERVED** | Read directly from data — the benchmark's generated observations, or an already-resolved historical outcome. |
| **MODELED** | The output of a trained, evaluated classifier and its SHAP attributions. |
| **DERIVED** | Computed transparently from observed/modeled values by plain arithmetic — no model involved. |
| **SYNTHETIC ASSUMPTION** | A disclosed prototype rule or benchmark-generation choice, stated as an assumption, not a fact. |
| **AI-GENERATED** | Prose produced by the AI layer to explain the above — never a source of new numbers. |

This distinction is carried through every screen, every API response,
and every AI answer, so a user can always tell what is known, what is
modeled, what is a transparent calculation, and what is an assumption —
rather than experiencing Sentinel as one undifferentiated "the system
says" voice.

---

## 9. Current Product Architecture

At the product level, not the implementation level:

```
Merchant data / benchmark
    → Risk modeling
    → Risk explanation
    → Exposure
    → Liquidity
    → Simulation
    → Intervention
    → Incident response
    → Evidence readiness
    → AI explanation
    → Outcome memory
```

Implementation-level architecture (services, modules, API surface) is
documented separately in the repository's architecture documentation.

---

## 10. Product Differentiation

Sentinel does not claim that no one else provides these capabilities.
Its intended differentiation is in the combination and the framing:

- A **merchant-level** perspective, not a transaction-level score.
- Risk translated into **financial-continuity** terms a merchant can
  reason about, not left as an abstract probability.
- A single, connected **risk → explain → simulate → intervene**
  workflow, rather than disconnected point tools.
- **Bounded** intervention intelligence that is transparent and
  inspectable rather than an opaque recommendation engine.
- Incident and evidence readiness treated as part of the same
  intelligence chain that detected the risk, not a separate module.
- **Provenance-first AI orchestration** — the assistant explains
  verified state, it does not replace it.
- A stated, forward-looking **outcome-loop thesis** (below).

**Sentinel does not currently have a proven moat.** The long-term thesis
is the outcome loop:

```
Real merchant data → interventions → observed outcomes → merchant risk memory
    → intervention effectiveness → merchant/archetype-specific intelligence
    → compounding learning advantage
```

This is a future strategic thesis, not a current claim. The current
synthetic benchmark has no real post-intervention outcome data, and
nothing in the product claims otherwise.

---

## 11. Current Product Status

**CORE PRODUCT: NEAR COMPLETE / PRODUCT FREEZE PHASE.**

Already implemented and verified in the repository:

- Synthetic benchmark generator (50 merchants × 180 days, eight
  archetypes, reproducible)
- Dataset validation
- Feature engineering (55 causal features across 9 groups)
- Baseline ML models (historical threshold, logistic regression)
- Candidate ML models (Random Forest, XGBoost)
- Evaluation (precision/recall/F1/PR-AUC, false-positive cost, warning
  lead time, temporal stress testing)
- Calibration investigation
- SHAP explainability, with faithfulness verification
- Backend API (FastAPI, typed, read-only over the trained model and
  benchmark artifacts)
- Dashboard — six screens: Overview, Risk, Explainability, Simulator,
  Incident Response, Evidence
- What-if simulator
- Incident response workflow
- Evidence readiness engine
- AI orchestrator (mock provider by default; OpenAI and an
  OpenAI-compatible open-weight provider supported)
- Intervention intelligence (V1, deterministic)
- Merchant Risk Memory (V1, in-process, session-scoped)

Remaining work was scoped as **finishing and presenting**, not building
new product capability, and is now complete:

- Final integration QA and visual polish
- Marketing site (built and deployed)
- Research presentation and documentation in GitHub
- Demo / pitch video (recorded)
- Final submission QA

No new product features are planned before submission.

---

## 12. Future Direction

Potential evolution, contingent on real-world data becoming available:

```
Chargeback intelligence → Merchant risk intelligence → Intervention intelligence
    → Financial continuity → Broader merchant intelligence → Potential adjacent financial products
```

The long-term outcome-loop thesis:

```
Real merchant data → observed interventions → observed outcomes
    → merchant-specific learning → increasingly useful recommendations
```

Every claim in this section is a direction, not a current capability.
All of it depends on real-world data validation that does not yet exist.

---

## 13. Product Success Criteria

Success is defined around usefulness and trust, not vanity metrics:

- Earlier visibility into materially elevated risk.
- Understandable, verifiable risk drivers.
- A useful translation of exposure into continuity/liquidity terms.
- Actionable but explicitly bounded intervention guidance.
- A reliable, deterministic simulation workflow.
- Credible incident preparedness that never overstates what has
  actually been done.
- Grounded AI explanations that never outrun their verified context.
- Transparent uncertainty and provenance on every number shown.
- Eventually, measurable real intervention outcomes — once real data
  exists to measure them.

No numeric success targets are defined here beyond what is already
reported in the research evaluation, since none currently exist as
committed product targets.

---

## 14. Final Product Definition

Sentinel helps merchants see emerging chargeback risk early, understand
what is driving it, translate it into cash-flow consequences, test what
they could change, prepare if the risk materializes, and eventually
learn from what actually happened.

Sentinel does not replace payment-platform risk systems. It is designed
as a merchant-facing intelligence layer around risk, consequences,
action, and learning.
