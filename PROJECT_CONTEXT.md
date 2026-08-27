# SENTINEL — PROJECT CONTEXT

## Project
Sentinel is an independent prototype for the Razorpay Buildathon,
targeting Track 02 — AI Risk Manager.

## Core thesis

Sentinel is a merchant-facing chargeback and settlement continuity
intelligence platform.

It detects potential high-loss chargeback episodes early, quantifies expected chargeback exposure, translates that exposure into merchant-specific liquidity stress, explains observable drivers, allows bounded what-if simulation, identifies grounded intervention opportunities, prepares merchants for dispute response, and records intervention/simulation outcomes for future prioritization.

## Core loop

Observe
→ Detect
→ Quantify
→ Explain
→ Simulate
→ Intervene
→ Prepare
→ Respond
→ Observe Outcome
→ Remember

The intervention and memory layers extend the intelligence loop but do not change the underlying ML problem.

## Primary ML problem

Predict whether a merchant is likely to experience a materially
elevated chargeback-loss episode within a future prediction horizon.

We will experimentally evaluate 7-day, 14-day and 30-day horizons.
14 days is currently the primary candidate but is NOT locked until
evaluation determines which horizon provides useful warning lead time
and acceptable precision/recall.

## Secondary ML problem

Predict future chargeback exposure amount.

## Derived business metric

Liquidity stress =
predicted chargeback exposure / available merchant liquidity.

Liquidity stress is calculated transparently and is NOT an ML prediction.

## Important boundary

Sentinel must NOT claim to predict Razorpay's proprietary settlement
hold decisions, enforcement decisions, internal risk scores, or bank
decisions.

We only model observable merchant-level signals using synthetic data.

## Dataset

The public benchmark will be entirely synthetic and reproducible.

Initial prototype:
50 merchants × 180 days.

Final target:
~500 merchants × 365 days.

Merchant archetypes:
- D2C Fashion
- Electronics
- SaaS
- Travel
- Marketplace
- Education
- Quick Commerce
- Digital Goods

The generator must model:
- baseline behavior
- trend
- seasonality
- noise
- gradual event deterioration
- benign growth events
- compound risk events
- chargeback mechanisms
- fulfillment
- refunds
- liquidity

## Critical benchmark principle

Growth must NOT automatically equal risk.

The dataset must contain hard negatives such as:
- festival growth
- viral campaigns
- product launches
- payment-method shifts

where GMV rises substantially but chargeback/operational health remains normal.

The model should be challenged to distinguish healthy growth from deteriorating operations.

## Prediction features

Feature groups include:
- payment behavior
- refund behavior
- chargeback behavior
- fulfillment
- customer mix
- financial state
- merchant behavior
- temporal velocity/acceleration
- deviation from merchant-specific baseline

Target approximately 50–70 meaningful engineered features,
not hundreds of meaningless features.

## Data leakage

For a prediction date t, features may only use information available
at or before t.

The label uses future information only.

Train/validation/test must be split at merchant level.
No merchant may appear in both train and test.

A separate temporal stress test should also be performed.

## Models

Baseline:
- merchant historical threshold

Then:
- Logistic Regression
- Random Forest
- XGBoost

The final model must be selected based on evaluation,
not because it sounds sophisticated.

## Evaluation

Required:
- Precision
- Recall
- F1
- PR-AUC
- Calibration
- False-positive cost
- Warning lead time

For regression:
- MAE
- RMSE
- appropriate percentage error where meaningful

Signature metric:
Median warning lead time.

## Explainability

SHAP will be used for model explanations.

The LLM MUST NOT independently calculate risk.

The LLM receives verified model outputs and can:
- explain predictions
- summarize drivers
- run bounded simulations
- organize evidence
- draft response material

It must not fabricate evidence or claim certainty.

## Counterfactual simulation

The simulator modifies selected observable features,
runs the trained model on the modified feature vector,
and compares predicted exposure.

The UI must call this "modeled impact", not guaranteed savings
or causal impact.

## Dispute/evidence layer

Sentinel will model reason-code-specific evidence readiness.

Possible evidence:
- invoice
- delivery proof
- tracking
- refund confirmation
- customer communication
- service/access records

The system can identify missing evidence and prioritize cases.

It must NOT fabricate evidence or autonomously submit disputes
without explicit merchant confirmation.

## Intervention Intelligence

Sentinel may identify grounded, merchant-actionable intervention opportunities
from existing observable signals.

V1 intervention intelligence is deterministic and rule-based, not an ML
prediction and not an LLM-generated recommendation.

The initial intervention controls are limited to the existing bounded simulator:
- refund rate
- on-time fulfillment rate
- new-customer share

Recommendations must:
- be grounded in verified merchant context
- use explicit and inspectable decision rules
- explain why the intervention was suggested
- connect directly to the existing simulator
- never fabricate transaction-level problems or operational counts
- never claim guaranteed savings or causal impact

The simulator remains responsible for modeled counterfactual impact.
Intervention Intelligence is responsible for deciding what the merchant
should consider investigating or changing.

Any modeled change must be described as "modeled impact", not guaranteed
savings or causal impact.

## Merchant Risk Memory / Outcome Loop

Sentinel may maintain a lightweight structured record of intervention and
simulation activity.

V1 memory may contain:
- intervention_id
- merchant_id
- recommendation
- action_status
- timestamp
- simulated_impact
- outcome_status

The system must distinguish:
- simulated/model-derived outcomes
- merchant action status
- actual observed outcomes

The current synthetic benchmark does not provide real-world post-intervention
outcomes.

Therefore Sentinel must NOT:
- fabricate observed outcomes
- calculate intervention success rates without evidence
- claim that it has learned from interventions
- convert simulated impact into an observed outcome
- claim causal effectiveness

V1 memory is a prototype decision-history layer, not a validated learning
system.

Future outcome learning may be investigated only when actual outcome data
exists and can be evaluated.

## Product modules

1. Risk Engine
2. Explainability
3. Liquidity/Continuity Intelligence
4. What-if Simulator
5. Intervention Intelligence
6. Incident/Dispute Response
7. Evidence Readiness
8. Merchant Risk Memory / Outcome Loop
9. AI Orchestrator

## Product responsibility boundaries

Risk Engine:
Predicts elevated future chargeback-loss episode risk using the evaluated
benchmark model.

Explainability:
Explains verified model behavior using SHAP.

What-if Simulator:
Tests bounded changes to existing observable features and reports modeled
impact.

Intervention Intelligence:
Identifies what the merchant should consider investigating or changing,
using deterministic rules grounded in verified context.

Incident / Evidence:
Organizes detected risk events and evidence readiness without fabricating
documents or submitting disputes autonomously.

Merchant Risk Memory:
Records intervention/simulation state and distinguishes simulated outcomes
from actual observed outcomes.

AI Orchestrator:
Explains and organizes verified outputs from these systems. It does not
independently calculate risk, generate recommendations from unsupported
information, or invent evidence.

## Visual direction

The actual dashboard should feel like serious premium fintech software.

The dashboard should expose the intelligence progression from risk detection → explanation → simulation → intervention → response, while remaining primarily 2D and operationally usable.

The marketing site will be cinematic and 3D.The marketing site should communicate the research journey:
question → investigation → falsification → hypothesis → experiment →
results → failures → intervention → strategic opportunity.

The marketing site must distinguish the current synthetic benchmark from
future scale targets and must not present hypothetical or future capabilities
as validated results.

The product itself should remain primarily 2D and highly usable.

The 3D experience is for:
- marketing
- storytelling
- pitch opening
- visualizing transaction/risk networks

Avoid turning the actual dashboard into a gimmicky 3D interface.

## Submission

The submission should include:

1. Working product
2. Cinematic 3D marketing website
3. 5-minute pitch video
4. Highly polished GitHub repository
5. Architecture documentation
6. Research documentation
7. Evaluation methodology
8. Failure cases
9. Security/AI guardrails
10. Honest limitations

## Engineering philosophy

Do not fabricate metrics.

Do not claim proprietary Razorpay data.

Do not claim that Sentinel predicts Razorpay's internal risk decisions.

Do not claim no competitor has similar technology unless verified.

Distinguish clearly between:
- verified facts
- research findings
- inference
- synthetic benchmark results
- strategic hypotheses.

Prefer a smaller number of genuinely working features
over many superficial AI features.

The ML engine must work before the UI is polished.

## Current implementation order

1. Synthetic data generator
2. Dataset validation
3. Baseline models
4. Candidate ML models
5. Evaluation
6. Calibration investigation
7. Explainability
8. Backend
9. Dashboard
10. Counterfactual simulator
11. Incident / evidence engine
12. AI orchestration
13. Intervention Intelligence
14. Merchant Risk Memory / Outcome Loop
15. Full product integration and QA
16. Product freeze
17. 3D marketing site
18. Pitch
19. Final documentation and submission polish