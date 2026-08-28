# SENTINEL — ARCHITECTURE

## 1. Overview

Sentinel is an independent merchant-facing risk intelligence prototype for the Razorpay Buildathon, targeting Track 02 — AI Risk Manager.

The architecture is intentionally layered. Synthetic data and machine-learning artifacts provide the predictive foundation; backend services provide authoritative risk and business logic; the frontend presents those verified outputs; the AI layer explains and orchestrates around verified context; and the intervention and memory layers extend Sentinel from prediction toward decision support and an eventual learning loop.

The central architectural principle is:

> The system that computes risk remains separate from the system that explains it.

Sentinel does not allow the AI layer to independently calculate risk, exposure, liquidity, intervention recommendations, or evidence readiness.

---

## 2. High-Level Architecture

```text
                           SENTINEL
                              │
                              ▼
                    ┌────────────────────┐
                    │ Synthetic Benchmark│
                    │   + ML Artifacts   │
                    └─────────┬──────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ Risk Engine │
                       └──────┬──────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       Explainability      Exposure         Liquidity
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    Counterfactual Simulator
                              │
                              ▼
                  Intervention Intelligence
                              │
                              ▼
                     Incident Response
                              │
                              ▼
                     Evidence Readiness
                              │
                              ▼
                       AI Orchestrator
                              │
                              ▼
                     Merchant Risk Memory
                              │
                              ▼
                    Future Outcome Learning
```

---

## 3. Repository Architecture

```text
sentinel/
│
├── apps/
│   └── dashboard/
│       ├── public/
│       └── src/
│           ├── api/
│           ├── components/
│           ├── hooks/
│           ├── lib/
│           ├── pages/
│           └── ...
│
├── backend/
│   ├── ai/
│   │   ├── context_builder.py
│   │   ├── guardrails.py
│   │   ├── orchestrator.py
│   │   ├── prompt.py
│   │   ├── response_parser.py
│   │   └── providers/
│   │       ├── base.py
│   │       ├── mock_provider.py
│   │       ├── openai_provider.py
│   │       ├── featherless_provider.py
│   │       └── factory.py
│   │
│   ├── api/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── state.py
│   │   └── main.py
│   │
│   ├── interventions/
│   │   ├── rules.py
│   │   └── recommendation_service.py
│   │
│   ├── memory/
│   │   └── risk_memory_service.py
│   │
│   └── risk/
│       ├── risk_service.py
│       ├── confidence_service.py
│       └── ...
│
├── ml/
│   ├── data/
│   ├── features/
│   ├── models/
│   └── ...
│
├── data/
├── scripts/
├── tests/
│
└── docs/
    └── architecture/
```

The repository separates experimentation and ML artifacts from backend services, frontend presentation, testing, and documentation.

---

## 4. Data and ML Layer

The public benchmark is synthetic and reproducible.
The ML pipeline follows:

```text
Synthetic Data Generation
          ↓
Dataset Validation
          ↓
Feature Engineering
          ↓
Historical Baseline
          ↓
Candidate Models
          ↓
Evaluation
          ↓
Calibration Investigation
          ↓
SHAP Explainability
          ↓
Trained Model / Artifacts
```
The primary ML problem is predicting whether a merchant is likely to experience a materially elevated chargeback-loss episode within a future prediction horizon.

A secondary modeling problem concerns future chargeback exposure.

The benchmark is designed to contain both deteriorating merchants and hard negatives where strong growth does not automatically imply elevated risk.

Sentinel does not use or claim access to Razorpay proprietary merchant data, proprietary risk scores, settlement enforcement decisions, internal risk systems, or bank decisions.

---

## 5. Feature Engineering and Leakage Boundary

For a prediction date t, model features may only use information available at or before t.
```text
Prediction date t
       │
       ├── Features
       │     └── information available ≤ t
       │
       └── Label
             └── future information after t
```
Feature groups include:

-payment behavior
-refund behavior
-chargeback behavior
-fulfillment
-customer mix
-financial state
-merchant behavior
-temporal velocity and acceleration
-deviation from merchant-specific baselines

The benchmark also contains benign growth scenarios such as campaigns, launches, and payment-method shifts so that growth itself is not treated as equivalent to risk.

Train/validation/test methodology uses merchant-level separation, with temporal stress testing used as an additional evaluation dimension.

---

## 6. Risk Engine

The Risk Engine is the authoritative source of Sentinel's merchant risk assessment.
Conceptually:

```text
Merchant State
      ↓
Feature Vector
      ↓
Trained Model
      ↓
Risk Assessment
```

The risk service exposes the verified model output used by downstream components.

The frontend does not independently calculate the risk probability.

The AI layer also does not calculate a separate risk probability.

This ensures that there is one authoritative source for risk calculations.

---

## 7. Exposure Intelligence

Sentinel translates predicted risk into modeled future chargeback exposure.
Conceptually:

```text
Risk assessment
      ↓
Exposure modeling
      ↓
Modeled chargeback exposure
```

Exposure is presented as a modeled quantity.
It is not presented as:

-a guaranteed future loss
-a guaranteed merchant liability
-a causal estimate
-a Razorpay settlement decision

The distinction between modeled and observed quantities is preserved throughout the product.

---

## 8. Liquidity and Continuity Intelligence

Sentinel translates modeled chargeback exposure into a merchant-facing financial continuity metric.

The prototype defines:

Liquidity Stress =
Predicted Chargeback Exposure
/
Available Merchant Liquidity

Liquidity stress is a derived metric.

It is not an independent machine-learning prediction.

The purpose of this layer is to translate abstract risk into a business consequence that a merchant can understand in terms of financial continuity.

The system does not claim that the modeled liquidity value represents a real merchant bank balance or proprietary settlement ledger.

---

## 9. Explainability Architecture

Sentinel uses SHAP-based explainability to expose the model signals contributing to a prediction.

```text
Risk Prediction
      ↓
SHAP Explanation
      ↓
Ranked Contributing Signals
      ↓
Merchant-Facing Explanation
```

The explainability layer operates independently from the LLM.

SHAP values describe model behavior and contribution to the prediction. They are not presented as proof of causal relationships.

The AI may explain these verified drivers but does not replace the underlying explainability computation.

---

## 10. Confidence and Data Quality

Sentinel includes a deterministic confidence/data-quality layer.
The confidence level is derived from grounded system conditions such as:

-available merchant history
-feature coverage
-The classification is qualitative rather than an invented probability.
-High
-Medium
-Limited

The confidence service reads conditions already resolved by the risk/data pipeline rather than asking the LLM to estimate confidence.

The AI may explain the supplied confidence level and its limitations, but it cannot independently create a confidence percentage or upgrade/downgrade the system's classification.

Confidence is not presented as a substitute for model calibration.

---

## 11. Counterfactual Simulator

The simulator is the authoritative source for counterfactual and modeled-impact calculations.

```text
Current Merchant State
          ↓
User Changes Supported Control
          ↓
Modified Feature State
          ↓
Existing Trained Model
          ↓
Simulated Result
          ↓
Comparison With Current State
```

The current supported simulator controls are:
-refund rate
-on-time fulfillment rate
-new-customer share
-The simulator is deliberately bounded.

Its output is labeled:

MODELED IMPACT

rather than:
-guaranteed savings
-guaranteed loss reduction
-causal impact
-guaranteed future outcome

No frontend component creates a second simulation engine.

Intervention Intelligence also delegates numerical simulation to this existing simulator.

---

## 12. Intervention Intelligence

Intervention Intelligence is a deterministic decision layer built on top of existing observable signals and the existing simulator.

```text
Observed / Verified Signal
          ↓
Deterministic Intervention Rule
          ↓
Ranked Recommendation
          ↓
Test in Simulator
          ↓
Existing Simulator
          ↓
Modeled Impact
```

The current V1 implementation considers only the three existing simulator controls.
Recommendations are grounded in merchant-specific signal deviations and corroborating model/explainability context.

The recommendation system does not invent transaction-level operational data.

Priority is deterministic and based on the relationship between the recommendation's signal and the merchant's current explainability context.

Intervention Intelligence does not claim to be an autonomous AI decision-maker.

Its role is to identify grounded operational levers that the merchant can investigate and test.

---

## 13. Intervention-to-Simulator Integration

The intervention layer does not create a second what-if engine.
When a merchant selects:

Test in Simulator

the frontend navigates to the existing simulator with the relevant control identified.

```text
Intervention Recommendation
          ↓
      Control ID
          ↓
Existing Simulator
          ↓
Merchant adjusts control
          ↓
Run simulation
          ↓
MODELED IMPACT
```

The simulator remains the sole source of counterfactual numbers.
This preserves a single source of truth for simulation mathematics.

---

## 14. Incident Response Architecture

Sentinel transitions from prevention to response when a relevant incident is identified.

```text
Risk / Incident Signal
          ↓
Incident Selection
          ↓
Incident Context
          ↓
Response Preparation
          ↓
Evidence Readiness
```

Incident information remains merchant-scoped.
Cross-merchant incident access is rejected.

The incident layer does not claim access to Razorpay's internal dispute systems.

---

## 15. Evidence Readiness Architecture

Sentinel models whether relevant evidence is available or ready for incident response.
Possible evidence categories include:

-invoice
-delivery proof
-tracking
-refund confirmation
-customer communication
-service/access records

-The evidence architecture follows:

```text
Incident
   ↓
Evidence Requirements
   ↓
Available / Missing Evidence
   ↓
Readiness State
   ↓
Response Preparation
```

Missing evidence remains missing.
Sentinel does not fabricate evidence or create fake transaction-level documents.

There is no autonomous external dispute submission path.

Any response material generated by the system is explicitly treated as draft material requiring merchant confirmation.

---

## 16. AI Orchestrator Architecture

The AI Orchestrator sits above Sentinel's verified product services.
```text
                 VERIFIED SENTINEL SERVICES
                            │
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
             Risk      Simulator      Incident
              │             │             │
              └─────────────┼─────────────┘
                            ↓
                    Context Builder
                            ↓
                       Guardrails
                            ↓
                       LLM Provider
                            ↓
                    Response Parser
                            ↓
                     Grounded Answer
```

The AI context is represented through the SentinelAIContext structure.
The context is assembled from existing authoritative service calls rather than independently computed by the AI layer.

The orchestrator can provide grounded explanations involving:

-risk
-risk drivers
-exposure
-liquidity
-simulation
-incidents
-evidence readiness
-intervention recommendations
-confidence/data quality
-draft response material

The AI does not become a second risk engine.

---

## 17. AI Provider Architecture

```text
The AI provider layer uses a small provider abstraction.
                       LLMProvider
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
           Mock         OpenAI       Featherless
         Provider      Provider       Provider
```

# Mock Provider
The mock provider is deterministic and does not require network access.
It is useful for development, testing, and predictable local verification.

# Featherless Provider
The Featherless implementation uses the same provider abstraction and OpenAI-compatible SDK interface with a configurable base URL and model.
The current real-provider integration can use:

openai/gpt-oss-20b

through Featherless.
Provider selection is configuration-driven.

The provider implementation does not alter Sentinel's underlying risk, simulation, intervention, incident, or evidence logic.

---

## 18. AI Grounding and Guardrails

The AI pipeline has multiple protection layers.

```text
User Question
      ↓
Deterministic Injection Pre-filter
      ↓
Verified Sentinel Context
      ↓
Runtime System Rules
      ↓
LLM Provider
      ↓
Defensive Response Parsing
      ↓
Grounded Answer
```

The AI must not:

-independently calculate risk
-invent unsupported numerical values
-fabricate evidence
-fabricate merchant outcomes
-claim causal certainty
-claim access to proprietary Razorpay systems
-change the supplied confidence classification
-expose another merchant's incident information
-autonomously submit disputes

Prompt-injection attempts can be blocked before a provider call when they match deterministic blocking patterns.

Runtime system rules provide an additional layer of protection for subtler attempts.

These protections are layered safeguards, not an absolute guarantee against every possible adversarial prompt.

---

## 19. Numerical Integrity
Sentinel maintains a strict separation between numerical computation and language generation.
The architecture follows:

```text
Authoritative Service
       ↓
Verified Numerical Output
       ↓
Structured AI Context
       ↓
LLM Explanation
```

The LLM is not responsible for computing Sentinel's numbers.
Numbers presented as authoritative in AI responses originate from verified context.

Simulation numbers are produced by the simulator.

Risk probabilities are produced by the risk service.

Derived metrics such as liquidity stress are calculated by deterministic product logic.

This prevents the language model from becoming an uncontrolled numerical source.

---

## 20. Merchant Risk Memory

Risk Memory V1 establishes a minimal structured outcome-recording layer.

```text
Recommendation
      ↓
Merchant Action
      ↓
Server-side Simulation
      ↓
Memory Record
      ↓
Observed Outcome
```

Each record structurally distinguishes:

# Modeled simulation
What the existing simulator estimated.

# Recorded merchant action
What the merchant chose to record.

# Observed outcome
What actually happened after the action.
The current benchmark does not provide real intervention outcome data.

Therefore:

Outcome = NOT OBSERVED
The system does not fabricate intervention success rates.
The recommendation engine does not currently learn from Risk Memory.

The current memory store is in-process and resets when the backend restarts.

This is an intentional V1 limitation rather than a claim of production-grade persistence.

---

## 21. Future Outcome Loop

Risk Memory establishes the architectural boundary for a future learning loop.
The intended future architecture is:

```text
Real Merchant Data
        ↓
Risk Detection
        ↓
Intervention
        ↓
Merchant Action
        ↓
Observed Outcome
        ↓
Risk Memory
        ↓
Intervention Effectiveness
        ↓
Better Prioritization
        ↓
Future Risk
```

This future loop is not currently presented as a validated machine-learning system.
A real production implementation would require durable storage, reliable outcome collection, sufficient real merchant data, evaluation methodology, and safeguards against feedback-loop bias.

The long-term strategic thesis is that observed intervention outcomes could eventually make recommendations increasingly merchant- and archetype-specific.

---

## 22. Frontend Architecture

The Sentinel dashboard is a React/Vite application.
Its primary responsibility is presentation, interaction, and navigation.

```text
React Dashboard
      │
      ├── Pages
      │
      ├── Components
      │
      ├── Hooks
      │
      ├── API Client
      │
      └── UI / Visualization
              │
              ↓
           FastAPI
```

The frontend consumes typed API responses.
Authoritative calculations remain in backend services.

The dashboard currently provides:

-Overview
-Risk
-Explainability
-Simulator
-Incident Response
-Evidence
-Intervention Intelligence
-Risk Memory
-AI Assistant

The product itself remains primarily 2D and usability-focused.
The 3D experience belongs to the separate marketing/storytelling layer described later in this document.

---

## 23. API Architecture

The backend uses FastAPI to expose merchant-scoped API routes.
Conceptually:

```text
Frontend
   ↓
FastAPI Routers
   ↓
Pydantic Schemas
   ↓
Service Layer
   ↓
Authoritative State / ML Artifacts
```

API schemas create typed boundaries between backend services and the frontend.
Merchant-scoped requests preserve merchant isolation.

Provider failures are mapped to clean API errors rather than exposing raw provider exceptions.

Secrets are never returned to the frontend.

---

## 24. Backend State and Persistence

The prototype uses lightweight in-process state where temporary persistence is required.
Risk Memory V1 uses a structure conceptually equivalent to:

```text
memory_store
    merchant_id
        ↓
    list of records
```

This state resets when the backend restarts.
This is explicitly a prototype limitation.

A production implementation would replace this with durable persistent storage and appropriate transactional and access-control guarantees.

The decision to avoid introducing a database in the current prototype keeps the architecture small and focused while preserving the conceptual outcome-memory boundary.

---

## 25. Provenance Architecture

Provenance is a cross-cutting architectural principle throughout Sentinel.
The system distinguishes between:

```text
OBSERVED
    ↓
Information directly available from the benchmark/system state

MODELED
    ↓
Information produced by the trained model or simulator

DERIVED
    ↓
Information calculated transparently from authoritative values

SYNTHETIC
    ↓
Information belonging to the reproducible public benchmark

AI-GENERATED
    ↓
Language/explanation generated by the LLM
```

This distinction allows the product to communicate what is known, what is modeled, what is derived, what is synthetic, and what is generated as language.

Provenance is particularly important because Sentinel operates in a financial-risk context where unsupported certainty can be misleading.

---

## 26. Security and Trust Boundaries

The architecture separates application logic from provider credentials and configuration.
API keys are supplied through environment configuration and are not committed to the repository.

The frontend never receives AI provider credentials.

Provider exceptions are sanitized before being returned through the API.

Merchant-scoped routes enforce isolation.

Cross-merchant incident access is rejected.

The public benchmark is synthetic.

Sentinel does not claim to process real Razorpay merchant transaction data in its public benchmark.

Detailed security considerations are documented separately in SECURITY.md.

---

## 27. Testing Architecture

Sentinel uses automated backend and frontend tests to protect both numerical behavior and product behavior.
The test layers cover areas including:

synthetic data validation
feature engineering
model behavior
risk calculations
explainability
simulator behavior
intervention rules
Risk Memory
confidence/data quality
AI grounding
AI guardrails
provider behavior
API contracts
frontend components
page behavior
navigation
merchant isolation

Live verification is additionally used where appropriate to validate:
real UI rendering
end-to-end navigation
provider integration
simulator handoff
intervention flow
incident/evidence flows
AI behavior

The goal is not only to test individual components but to verify the complete merchant workflow.

---

## 28. End-to-End Product Flow

The complete product architecture can be understood as:

```text
OBSERVE
   ↓
DETECT
   ↓
QUANTIFY
   ↓
EXPLAIN
   ↓
SIMULATE
   ↓
INTERVENE
   ↓
RESPOND
   ↓
OUTCOME
   ↓
RISK MEMORY
   ↓
BETTER PRIORITIZATION
   │
   └──────────────→ FUTURE RISK
```
The first stages are implemented product capabilities.
The final learning loop remains intentionally limited because the current benchmark does not contain real observed intervention outcomes.

---

## 29. Primary User Journey

A typical merchant workflow is:

```text
Overview
   ↓
Understand current risk
   ↓
Inspect risk drivers
   ↓
Understand exposure / liquidity stress
   ↓
Review Intervention Intelligence
   ↓
Test a recommendation in Simulator
   ↓
Observe MODELED IMPACT
   ↓
Record the simulation/action
   ↓
Review Incident Response if risk materializes
   ↓
Check Evidence Readiness
   ↓
Ask the AI Assistant for grounded explanation
   ↓
Review Risk Memory
```

This flow connects prediction to decision support rather than treating each dashboard module as an isolated feature.

---

## 30. Marketing Website Architecture

The 3D marketing website is a separate presentation layer around Sentinel.
It is not the product dashboard and does not replace any backend or ML functionality.

Its purpose is to communicate:

the problem
the research journey
the product thesis
the system architecture
the Sentinel workflow
the strategic vision
The actual Sentinel product remains the 2D dashboard.
The marketing website is the cinematic narrative layer.

---

## 31. 3D Research Lab
The Research Lab is a section inside the 3D marketing website itself.
It is not a separate product or application.

Its purpose is to turn Sentinel's research process into a visual journey.

The intended sequence is:

```text
QUESTION
   ↓
LANDSCAPE
   ↓
CANDIDATE GAPS
   ↓
FALSIFICATION
   ↓
HYPOTHESIS
   ↓
EXPERIMENT
   ↓
RESULTS
   ↓
FAILURE ANALYSIS
   ↓
INTERVENTION
   ↓
FUTURE
```

The website should communicate the research as a discovery story:

```text
We started with a question.
        ↓
We investigated the payment ecosystem.
        ↓
We identified possible gaps.
        ↓
We tried to falsify them.
        ↓
One direction survived.
        ↓
We formed a hypothesis.
        ↓
We built an experiment.
        ↓
We tested it.
        ↓
We studied both results and failures.
        ↓
Sentinel emerged.
```

The website presents the high-level narrative.
The GitHub repository contains the deeper research evidence, methodology, artifacts, and technical documentation.

The two layers should complement each other rather than duplicate one another.

---

## 32. Research and Evidence Relationship

The research architecture is intentionally split into two experiences.
# 3D Marketing Website
The website provides the concise, cinematic research story.
It focuses on:

1. why the problem matters
2. what was investigated
3. what alternatives were considered
4. how the hypothesis was formed
5. how the experiment was designed
6. what was learned
7. where the system fails
8. how intervention emerged from the research
9. where the product could go next

# GitHub
GitHub provides the deeper evidence layer.
It contains:

1. research documentation
2. dataset methodology
3. experiment methodology
4. evaluation results
5. failure analysis
6. architecture documentation
7. security documentation
8. product documentation
9. reproducibility information
10. The website should link users to the deeper GitHub evidence where appropriate.

---

## 33. Final Marketing Website Destinations

At the end of the 3D marketing website, visitors will be given clear links to the three primary project destinations:
┌─────────────────────┐
│   GITHUB REPOSITORY │
└─────────────────────┘

┌─────────────────────┐
│     PITCH VIDEO     │
└─────────────────────┘

┌─────────────────────┐
│   LIVE PRODUCT      │
└─────────────────────┘
The Live Product link will be added after Sentinel is deployed.
The marketing website therefore functions as the narrative entry point into:

```text
Research
   ↓
GitHub Evidence

Product
   ↓
Live Dashboard

Story
   ↓
Pitch Video
```

---

## 34. Architectural Boundaries

Sentinel intentionally does not include:
1. Razorpay proprietary risk infrastructure
2. proprietary settlement-hold decisioning
3. proprietary internal risk scores
4. transaction-network fraud decisioning
5. autonomous dispute submission
6. fabricated evidence
7. fabricated intervention outcomes
8. causal claims from the simulator
9. LLM-controlled risk calculations
10. production-grade persistent Risk Memory
11. a validated real-world intervention-learning loop
12. a claim of guaranteed loss reduction
13. These are architectural boundaries, not missing features that the current prototype is required to implement.

---

## 35. What Each Layer Owns

| Layer                     | Responsibility                               |
| ------------------------- | -------------------------------------------- |
| Synthetic Data            | Reproducible benchmark generation            |
| Feature Engineering       | Constructing model inputs without leakage    |
| ML                        | Risk/exposure modeling                       |
| Risk Service              | Authoritative risk assessment                |
| Explainability            | Model-driver interpretation                  |
| Exposure                  | Modeled financial exposure                   |
| Liquidity                 | Derived continuity metric                    |
| Simulator                 | Authoritative counterfactual calculation     |
| Intervention Intelligence | Grounded deterministic recommendations       |
| Incident Response         | Incident context and response workflow       |
| Evidence                  | Evidence readiness                           |
| AI Orchestrator           | Grounded explanation and orchestration       |
| Risk Memory               | Structured action/simulation/outcome records |
| Frontend                  | Presentation and user interaction            |
| 3D Marketing Site         | Storytelling and research presentation       |
| GitHub Research           | Deep technical evidence and reproducibility  |

---

## 36. Architectural Principles

Sentinel follows these principles:

1. One authoritative source for each calculation.
2. The frontend does not recreate backend business logic.
3. The AI explains verified context rather than calculating risk independently.
4. Simulation remains bounded and explicitly non-causal.
5. Intervention recommendations remain grounded in observable signals.
6. Observed, modeled, derived, synthetic, and AI-generated information remain distinguishable.
7. Missing information is represented as missing rather than fabricated.
8. Merchant-scoped information remains isolated.
9. Prototype limitations are documented rather than hidden.
10. Future capabilities are not presented as currently validated capabilities.
11. Product complexity should remain proportional to demonstrated value.
12. Research evidence and product storytelling should complement rather than duplicate each other.

---

## 37. Architectural Summary

Sentinel is structured as a layered merchant intelligence system:
```text
DATA
 ↓
ML
 ↓
RISK
 ↓
EXPLANATION
 ↓
FINANCIAL CONSEQUENCE
 ↓
SIMULATION
 ↓
INTERVENTION
 ↓
RESPONSE
 ↓
AI ORCHESTRATION
 ↓
MEMORY
```
The core architectural idea is that each layer builds on verified outputs from the layer beneath it instead of creating competing sources of truth.
This allows Sentinel to evolve from a predictive risk prototype toward a broader merchant intelligence system while preserving a strict distinction between:

what the system observes, what the model predicts, what the system derives, what the simulator models, what the merchant records, what actually happened, and what the AI merely explains.
