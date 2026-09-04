# Sentinel Research

**Status of this document**: this is the narrative research record — *why*
Sentinel investigated the problem it investigated, what it tried to
falsify before building anything, what survived, and what did not.
Quantitative evidence lives in [`EVALUATION.md`](../../EVALUATION.md).
Implementation lives in [`ARCHITECTURE.md`](../../ARCHITECTURE.md) and
`docs/architecture/*.md`. Product behavior lives in
[`PRODUCT.md`](../../PRODUCT.md). This document does not repeat any of
those in detail — it explains the reasoning that connects them.

Sentinel was built for the Razorpay Buildathon, Track 02 — AI Risk
Manager, as an independent prototype with **no access to real Razorpay
data, real merchant transactions, or proprietary network infrastructure**.
Every external claim below is cited to a primary or high-authority
source, listed in full in [Sources](#sources) at the end of this
document. Every internal claim is either sourced to `EVALUATION.md`'s
verified results or explicitly labeled as project reasoning. Where a
claim could not be adequately sourced, it is either removed, labeled as
inference, or stated as an open question — not asserted as fact.

---

## 1. Question

**"What if merchant risk could be seen before the loss became
unavoidable?"**

The brief starting point for this project — build something in the
chargeback/risk space for a payments platform's Track 02 — could have
been answered narrowly: score a transaction, flag it, decline it. That
is a real, well-instrumented problem, and it is not the one this
project chose to investigate.

A chargeback is not a single-transaction event from the merchant's
side. When a cardholder disputes a charge, the issuer opens a formal
dispute against the card network, the payment is reversed immediately,
and the merchant is given a fixed window — commonly on the order of
weeks, not months — to accept the loss or submit evidence contesting it
[Razorpay, *About Disputes*][razorpay-disputes]. That structure already
tells you something important: by the time a chargeback exists as an
event, the merchant is reacting to something that has *already
happened*. The transaction is reversed before the merchant's evidence
is even reviewed.

The research question this project actually investigated was whether a
useful signal exists *earlier* than that — not "is this transaction
fraudulent," but a merchant-level, forward-looking question:

> Is this merchant heading toward a materially elevated risk episode,
> why, what could they change, and what could the financial consequence
> look like?

This reframing matters because a merchant does not experience risk as
an isolated probability. Federal Reserve Bank of Kansas City research
on U.S. card chargebacks found that merchants bear roughly 70–80% of
chargeback losses as merchant-liable outcomes, and that fraud is the
single most common chargeback reason, accounting for roughly half of
all chargebacks [Hayashi, Markiewicz & Sullivan, 2016][kcfed-chargebacks].
A merchant absorbing that liability does not just want to know "was
this transaction risky" after the fact — they want enough warning to
change something about their own operations before the exposure
compounds. That is a different consumer, a different point in the
timeline, and a different useful output than a transaction-decisioning
system provides.

**This is stated here as the hypothesis the research set out to
investigate, not as a proven or externally validated market gap.**
Section 4 (Falsification) describes how this framing was actively
challenged — including by asking whether it was even the right problem
to solve — before any of Sentinel's architecture was committed to.

---

## 2. Landscape

Before choosing a direction, the project mapped the existing categories
of payment-risk infrastructure — not as an exhaustive competitive
audit (none was performed, and none is claimed), but to understand
*which layer of the problem* each category actually operates on, and
where a gap might genuinely remain unaddressed.

```
TRANSACTION DECISIONING
    → authorization-time fraud/risk decisions
DISPUTE PREVENTION
    → pre-dispute intervention, before a formal chargeback exists
LIABILITY TRANSFER
    → chargeback guarantees / protection products
DISPUTE RESPONSE
    → evidence collection and automated response after a chargeback exists
MERCHANT ANALYTICS
    → reporting / visibility into what already happened
MERCHANT-LEVEL FORWARD-LOOKING INTELLIGENCE
    → the layer Sentinel proposes to occupy
```

**Transaction decisioning.** Operates at authorization time, on a
single transaction, consumed by the platform's own risk systems.
Output: approve / decline / step-up. Adyen's RevenueProtect, for
example, is described as combining machine learning with static rules
to analyze payment data and protect against fraudulent activity at this
layer [Adyen, *Manage Disputes*][adyen-disputes]. This is real,
mature infrastructure — and it is not what Sentinel is trying to
replace. Sentinel has no transaction stream, no authorization-time
hook, and does not claim one.

**Dispute prevention.** Operates in the narrow window *between* a
cardholder's complaint and a formal chargeback. Visa and Mastercard
each acquired a company built specifically for this layer — Visa
acquired Verifi in 2019, and Mastercard had already acquired Ethoca
earlier that year — consolidating "pre-dispute" alerting so a merchant
can be notified and refund a transaction before it escalates into a
chargeback [Digital Transactions, 2019][digitaltransactions-verifi].
Stripe's own dispute-prevention tooling documents this exact mechanism:
Verifi/Ethoca-style alerts plus "Compelling Evidence" data can "block
disputes entirely" before they are ever filed
[Stripe, *Dispute prevention*][stripe-prevention]. This is a real,
already-solved piece of the timeline for merchants on modern
processors — and it operates transaction-by-transaction, after a
complaint has already been raised, not on a merchant's trailing
operational trend before any single complaint exists.

**Liability transfer.** Chargeback-guarantee products absorb the
financial loss directly, in exchange for a fee — a fundamentally
different value proposition from prediction: it removes the pain
rather than explaining or forecasting it. Sentinel does not assume
liability, guarantee an outcome, or claim to eliminate loss anywhere in
the product (`PRODUCT.md` §7).

**Dispute response.** Operates after a chargeback has already been
filed: assembling and submitting evidence. Card networks provide
structured mechanisms for this — Visa's Dispute Resolution rules
describe an "Allocation Workflow" for automated, rules-based decisions
and a "Collaboration Workflow" for manual review of contested cases,
under the umbrella of Visa Claims Resolution (VCR), with a defined
window (Visa documentation cites 120 days from the transaction date for
most dispute types, longer for specific categories such as recurring
or fraud-flagged transactions) [Visa, *Dispute Management Guidelines
for Visa Merchants*, June 2024][visa-dmg]. Stripe's own "Smart
Disputes" feature — an AI system that assembles and submits evidence
packets automatically — sits squarely in this layer
[Stripe, *Dispute prevention*][stripe-prevention]. Sentinel's own
incident/evidence-readiness layer is explicitly **not** this: it
prepares readiness signals and never submits, files, or automates a
response (`docs/architecture/incident_response.md`).

**Merchant analytics.** Reporting and dashboards that show a merchant
what has already happened — dispute activity, dispute rate, historical
trends. Stripe's own measurement tooling is a clean example: it
reports "dispute activity" and "dispute rate" and states that the
credit-card-processing industry recognizes dispute activity above
**0.75%** as excessive, a threshold that can trigger placement in a
card-network monitoring program [Stripe, *Measuring
disputes*][stripe-measuring]. This is valuable, real infrastructure —
and it is retrospective by construction. It tells a merchant where
they have been, not where they are heading.

**Merchant-level, forward-looking intelligence.** The layer Sentinel
chose. None of the five categories above are built to answer "is this
specific merchant's trailing operational behavior currently drifting
toward an elevated-loss episode, and what could they do about it before
it becomes a chargeback statistic." Regulatory infrastructure in
India adds a relevant data point here: RBI's Turn Around Time (TAT)
framework for failed transactions sets fixed auto-reversal windows
(T+1 day for UPI/IMPS-class transfers, T+5 days for card and e-commerce
transactions) and a standard compensation rate of ₹100 per day of delay
beyond that window, applied automatically without requiring a
customer complaint [RBI, *Harmonisation of TAT and customer
compensation for failed transactions*, 2019][rbi-tat]. That framework
exists because failed and disputed transactions were, at scale, a
customer-experience and operational problem serious enough to warrant
a national regulatory response — evidence that timely resolution in
payments is treated as materially important by the regulator, not
merely a nice-to-have for the ecosystem this project sits inside.

**This is deliberately not framed as "nobody else does this."** No
formal, exhaustive competitive study was performed. The five categories
above are real, are operated by well-resourced companies and networks,
and several of them (dispute prevention in particular) already address
part of the timeline this project cares about. The defensible framing
is narrower: Sentinel chose to occupy a specific, comparatively
underexplored layer — merchant-level, forward-looking, decision-
oriented intelligence — rather than compete with transaction
decisioning, liability transfer, or dispute-response infrastructure
that already exists and that a synthetic-benchmark prototype has no
basis to claim it improves on.

---

## 3. Candidate Problems

Once the layer was chosen, the research still had to decide *which*
capabilities within that layer were worth building. Nine candidates
were considered. This is presented as a decision record, not a feature
list — including the reasoning for what was deferred or left as future
work, not only what shipped.

| # | Candidate | Question | Decision | Status |
|---|---|---|---|---|
| 1 | Forward-looking merchant risk | Can a model separate "heading toward an elevated episode" from normal variation, at a useful horizon? | Directly tests the core hypothesis (§5) — must be built first, everything else depends on it | **Implemented** — `EVALUATION.md` §5 |
| 2 | Liquidity / continuity intelligence | Does a merchant care more about a probability, or what it means for cash flow? | A bare probability is hard to act on; a continuity framing is the more decision-relevant translation | **Implemented** — transparent derivation, not a second model (`PRODUCT.md` §5.4) |
| 3 | Early-warning lead time | Does the model's warning arrive with enough runway to matter? | This is the entire point of "forward-looking" — without measured lead time, the claim is unfalsifiable | **Implemented and evaluated** — became the project's signature metric, §6–8 below |
| 4 | Counterfactual simulation | Can a prediction become a decision tool rather than a static number? | Directly addresses the falsification concern that "a dashboard doesn't change behavior" (§4) | **Implemented** — bounded what-if simulator, three controls |
| 5 | Evidence readiness | Once risk materializes, is the merchant prepared to respond? | Extends the loop from prevention into response, without claiming to automate response | **Implemented** — incident/evidence workflow |
| 6 | Intervention Intelligence | Can a detected signal be connected to a concrete operational lever? | Directly answers "prediction without action is another ignored dashboard" (§4) | **Implemented, V1, deterministic** — §9 below |
| 7 | Risk Memory / outcome loop | Can the system eventually learn which interventions work? | The most ambitious candidate — and the one most at risk of overclaiming without real data | **Implemented as scaffolding only** — records activity; outcome is always `not_observed`. The *learning* half is a research direction, not a built capability — §10 below |
| 8 | Confidence / data-quality transparency | Should every risk read carry the same implied certainty? | A model's own limitations should be visible at the point of use, not only in a report | **Implemented, V1** — `docs/architecture/confidence_data_quality.md` |
| 9 | Settlement-hold survivability, network-threshold proximity, lending bridge | Could Sentinel extend beyond chargeback risk into related continuity questions? | Plausible extensions of the same thesis, but untested and out of scope for this benchmark | **Not implemented — future research only**, §11 |

**Candidates 1–8 are grounded in this project's own reasoning about the
problem (§1–§2), not in externally researched market evidence that
these specific product shapes are in demand.** Where a candidate's
motivation draws on an external fact — e.g., candidate 3's premise that
warning lead time matters because dispute response windows are short
and fixed [Visa, 2024][visa-dmg] — that connection is noted, but the
decision to build the candidate itself was project reasoning, not a
validated market finding. Candidate 9 remains explicitly conceptual:
no research, external or internal, was performed to test settlement-
hold survivability or network-threshold proximity as predictive
problems, and nothing about them should be read as existing in the
current codebase.

---

## 4. Falsification

This is treated as the most important chapter of this research record,
not a formality before the "real" engineering work. The project
deliberately did not start from a fixed feature list and build outward.
Before committing to §5's hypothesis, the central question asked was:

> **What would make this thesis NOT worth building?**

Ten counter-hypotheses were considered. Each is presented in the same
form: the concern, why it could plausibly be true, how Sentinel's
architecture constrains or responds to it, what the evidence (where any
exists) actually shows, and what remains genuinely unresolved.

**H1 (the thesis being tested): merchant-level temporal signals contain
useful forward-looking information about elevated chargeback risk.**

**C1 — A transaction-level fraud system might already solve the
economically important problem.**
*Why it could be true*: transaction decisioning is mature, well-funded
infrastructure (§2), and roughly half of chargebacks are fraud-related
in the first place [Hayashi et al., 2016][kcfed-chargebacks].
*How Sentinel constrained it*: Sentinel does not compete at this layer
at all — no transaction stream, no authorization hook (§2).
*What the evidence shows*: no evidence either way was gathered on
whether transaction-level systems "solve" the merchant-level continuity
problem — this was not something Sentinel's benchmark could test, since
it has no transaction-level ground truth to compare against.
*Unresolved*: whether a merchant who already has good transaction-level
fraud coverage still benefits from a merchant-level forward-looking
view is an open question, not answered here.

**C2 — Dispute prevention (pre-dispute alerting) could make
merchant-level prediction unnecessary.**
*Why it could be true*: Verifi/Ethoca-style alerts already give
merchants a window to refund a transaction before it becomes a formal
chargeback [Stripe, *Dispute prevention*][stripe-prevention].
*How Sentinel constrained it*: pre-dispute alerting operates
transaction-by-transaction, after a specific complaint exists. It says
nothing about a merchant's trailing operational trend before any single
complaint has been raised — a different question in a different time
window.
*Unresolved*: whether the two are complementary or substitutable in
practice was not tested; this is project reasoning about scope, not a
measured comparison.

**C3 — Liability transfer (a chargeback guarantee) could be more
valuable to a merchant than prediction.**
*Why it could be true*: guarantees remove the financial pain directly;
prediction only explains it.
*How Sentinel constrained it*: Sentinel does not attempt to compete on
this axis and says so explicitly (`PRODUCT.md` §7) — it is not a
lending or liability product today.
*Unresolved*: genuinely, for a given merchant, which is more valuable —
this is a real open business question this project did not investigate.

**C4 — A generic risk dashboard might not change merchant behavior.**
*Why it could be true*: a static score a merchant checks once and
ignores has limited real value — this is a recognized weak point of
"analytics" as a category (§2).
*How Sentinel constrained it*: this concern is the direct origin of the
product's progression past a risk score into explanation, financial
translation, simulation, and intervention (§9) — the architecture does
not stop at a badge.
*Unresolved*: whether merchants using Sentinel's actual product would
behave differently as a result is untested — this benchmark has no
mechanism to observe merchant behavior change at all.

**C5 — Prediction without actionable intervention could become another
ignored dashboard.**
*Why it could be true*: closely related to C4, and the direct
motivation for candidate 6 in §3.
*How Sentinel constrained it*: Intervention Intelligence exists
specifically so a detected signal connects to something a merchant can
test, not just observe (§9).
*Unresolved*: whether the three specific levers Sentinel exposes
(refund rate, on-time fulfillment, new-customer share) are the levers
that actually matter to a real merchant is unvalidated.

**C6 — A model might confuse legitimate growth with deterioration.**
*Why it could be true*: this is a well-known failure mode for any
model trained on volume-correlated features — a merchant's best month
could look identical to a merchant heading into trouble if growth
itself is treated as the risk signal.
*How Sentinel constrained it*: the synthetic benchmark was deliberately
built with hard-negative growth scenarios from the start (festival
growth, viral campaigns, product launches, payment-method shifts) that
raise GMV without elevating chargeback/refund/fulfillment metrics.
*What the evidence shows*: the growth-vs-risk contrast held in
aggregate, but not uniformly at the individual-scenario level — one
hard-negative type showed a 0% false-positive rate while another showed
a 100% false-positive rate on a small sample (`EVALUATION.md` §9). This
is a genuine, partial result, not a clean pass — see §7 and §8 below.

**C7 — Offline performance might disappear under temporal
distribution shift.**
*Why it could be true*: a model can look strong on a held-out sample
from the same time period it trained on and still fail once real time
passes and merchant behavior drifts.
*How Sentinel constrained it*: a dedicated temporal stress test held
out a later time window the model never trained on, for the same test
merchants.
*What the evidence shows*: performance degraded materially under this
stress test (PR-AUC 0.603 → 0.476 at the 30-day horizon,
`EVALUATION.md` §7) — a real, non-trivial weakness, not a clean pass.

**C8 — Short warning horizons might provide insufficient runway to be
useful.**
*Why it could be true*: if the earliest reliable warning arrives only
a day or two before the episode, "forward-looking" is a technicality,
not a practical advantage.
*What the evidence shows*: separation from chance rose sharply with
horizon (7-day PR-AUC 0.262 vs. 30-day PR-AUC 0.603) — the 7-day
horizon in particular is weak enough that this concern is **partially
validated**: a one-week warning window, on this benchmark, adds little
over chance (`EVALUATION.md` §5, §7 below).

**C9 — Simulator outputs could create false causal confidence.**
*Why it could be true*: a "what happens if I change X" tool is
dangerous if it implies a guarantee.
*How Sentinel constrained it*: every simulator result is labeled
"MODELED IMPACT," the product language never uses causal or guarantee
words, and this is enforced by automated tests
(`docs/architecture/simulator.md`, `EVALUATION.md` §12).
*Unresolved*: whether users correctly internalize a disclaimer, versus
just trusting the number shown, is a real UX/behavioral question no
benchmark can answer.

**C10 — An intervention system without real outcome data could pretend
to learn when it does not.**
*Why it could be true*: this is the single most structurally dangerous
failure mode on the list — a system that implies it has learned
something it has not.
*How Sentinel constrained it*: Merchant Risk Memory's `outcome_status`
is hardcoded to `not_observed` for every record the system can ever
produce, and the recommendation engine never reads its own memory store
— structurally, not just by convention (`EVALUATION.md` §13, §9 below).
*Unresolved*: nothing — this is fully closed by construction. The
system cannot claim to have learned, because no code path allows it to.

**What falsification did and did not establish.** The research did
**not** attempt to prove any of the ten alternatives above is inferior
to Sentinel — several of them (C2, C3 in particular) plausibly deliver
faster, more direct value for a merchant, and none were evaluated
head-to-head. Two concerns (C6, C7, C8) were tested directly and
produced genuinely mixed results, retained honestly rather than
smoothed over (§7–§8). The goal was narrower and more disciplined: find
a problem layer, and a set of claims within it, that a synthetic-
benchmark prototype could actually build and honestly evaluate —
without pretending to the network-scale data, balance sheet, or
proprietary infrastructure that liability-transfer or enterprise fraud
platforms depend on.

---

## 5. Hypothesis

What survived §1–§4 is the hypothesis this project actually tested:

> A merchant-level system can use temporal behavioral and operational
> signals to identify materially elevated future chargeback-loss
> exposure early enough to provide useful warning, explain the
> observable drivers, translate the risk into financial/continuity
> consequences, and let the merchant test bounded operational
> interventions before responding to an incident.

Broken into individually testable claims, each linked to the exact
evidence in `EVALUATION.md`:

| Claim | Null hypothesis | Evidence / metric | Result | Status |
|---|---|---|---|---|
| Risk can be predicted from merchant-level temporal signals | Model performance is indistinguishable from chance | PR-AUC vs. base rate, all horizons (`EVALUATION.md` §5) | 30d PR-AUC 0.603 vs. ~28.6% base rate; clear separation | **SUPPORTED ON SYNTHETIC BENCHMARK** |
| Warning can occur before the modeled risk episode | The model only detects an episode on or after it has already started | Warning lead-time analysis (`EVALUATION.md` §8) | Median 7.0 days sustained lead time at 30d, after a measurement bug was corrected (§8 below) | **SUPPORTED ON SYNTHETIC BENCHMARK** |
| A 7-day horizon provides useful early warning | 7-day performance is not meaningfully above chance | 7d PR-AUC 0.262 vs. base rate ~18-21% | Weak separation; all models cluster near the random-baseline PR curve | **NOT SUPPORTED** at 7 days on this benchmark |
| Benign growth can be distinguished from deterioration | The model cannot separate growth from risk; hard negatives trigger false positives at the same rate as risk episodes | Hard-negative scenario audit (`EVALUATION.md` §9) | Holds in aggregate; fails badly on one scenario type (n=7) | **PARTIALLY SUPPORTED** |
| Model behavior can be explained | SHAP attributions do not reconstruct the model's actual output | Faithfulness check (`EVALUATION.md` §10) | Max reconstruction error ~3×10⁻¹⁵ (machine precision) | **SUPPORTED ON SYNTHETIC BENCHMARK** (mechanically — not a causal claim) |
| Risk can be translated into exposure/liquidity language | The translation cannot be made transparently without a second unvalidated model | Exposure = disclosed trailing-average derivation, not a model (`EVALUATION.md` §12) | Implemented as a transparent, disclosed calculation | **IMPLEMENTED, NOT A PREDICTIVE CLAIM** |
| Bounded simulator controls can turn prediction into decision support | Simulator results are not reproducible/deterministic, or leak state | Determinism, isolation, mutation tests (`EVALUATION.md` §12) | All structural guarantees verified | **IMPLEMENTED BUT NOT CAUSALLY VALIDATED** |
| Intervention recommendations can be grounded in observable signals | Recommendations fire on noise, not genuine deviation | Empirical z-threshold calibration against the full benchmark distribution (`EVALUATION.md` §13) | Threshold selects the most-deviated ~17-19% of rows per control; most merchant-days show zero recommendations | **IMPLEMENTED, GROUNDED — NOT VALIDATED AS EFFECTIVE** |
| Incident/evidence workflows can connect prevention with response | Incidents are invented rather than grounded in real detected episodes | Independent recomputation of the detection rule (`EVALUATION.md` §14) | Detection bar matches exactly; 50 of 80 risk episodes across 34 of 50 merchants surfaced | **SUPPORTED ON SYNTHETIC BENCHMARK** |

**Every "SUPPORTED" status above is supported only by the synthetic
benchmark described in §6.** None of these claims — including the two
most rigorously evaluated (predictive performance, warning lead time)
— has been validated against real merchant data, a real merchant's
actual behavior, or a real dispute outcome. That boundary is load-
bearing for how every number in this document and in `EVALUATION.md`
should be read, not a closing caveat.

---

## 6. Experiment

**Why synthetic data was necessary.** Sentinel is an independent,
public prototype with no access to real Razorpay data, real merchant
transactions, or proprietary risk signals. A public research artifact
built on real payment data would not be possible responsibly or legally
in this context. A fully synthetic, reproducible benchmark was the only
path that let the project test its hypothesis at all.

**What synthetic data allows.** Full control over ground truth (the
generator knows exactly which merchant-days are genuinely risk-driven
vs. benign growth, because it wrote the scenario), full reproducibility
(one fixed seed regenerates byte-identical data), and the ability to
deliberately engineer the exact adversarial cases the falsification
chapter (§4, C6) demanded — hard negatives that look like risk but
are not.

**What synthetic data cannot establish.** Real-world predictive
validity, real merchant behavior, real fraud patterns, real dispute
outcomes, or anything about how a real payments ecosystem's actual
distribution of risk compares to a generator's designed assumptions.
This is the project's single largest limitation, stated here and
repeated at every relevant point below.

**The benchmark actually used**: 50 merchants, 180 days, 9,000
merchant-days, 140 scheduled scenario events (26 festival-growth, 21
fulfillment-degradation, 18 chargeback-deterioration, 17 refund-shock,
16 compound-risk, 13 viral-campaign, 11 payment-method-shift, 10
product-launch, 8 customer-mix-shift), 55 engineered features, one
fixed random seed (`EVALUATION.md` §2). **A larger benchmark (roughly
500 merchants × 365 days) is a planned expansion of the same generator
code path, not the benchmark this evaluation was run on** — every
result in this document and in `EVALUATION.md` is the 50×180 run, and
nothing here should be read as describing the larger scale.

**Experimental pipeline, as actually run:**

```
DATA GENERATION
    → FEATURE ENGINEERING
    → TARGET CONSTRUCTION
    → BASELINE
    → MODEL COMPARISON
    → TEMPORAL STRESS
    → CALIBRATION
    → EXPLAINABILITY
    → EARLY WARNING
    → HARD NEGATIVES
    → SIMULATOR
    → INTERVENTION
    → INCIDENT / EVIDENCE
    → AI GROUNDING
```

**Why each methodological principle was treated as non-negotiable:**

- **Merchant-level separation** — because the useful claim is "this
  generalizes to a merchant the model has never seen," not "this
  memorizes patterns within merchants it already trained on." No
  merchant appears in more than one of train/validation/test.
- **Prediction-time feature boundary and future label separation** —
  because a model that can see the future during training proves
  nothing about early warning; every feature uses only information at
  or before the prediction date, and the label is built only from
  strictly later data.
- **Temporal stress testing** — because C7 (§4) is a real risk for any
  model evaluated only on data from the same period it trained on; a
  later, never-trained-on window is the only honest test of drift
  survival.
- **Hard negatives / benign growth** — because C6 (§4) is the failure
  mode that would make Sentinel commercially dangerous, not just
  inaccurate; the benchmark was built to actively probe for it, not
  assumed away.
- **Multiple horizons** — because "forward-looking" is meaningless
  without asking *how far* forward is actually useful (C8, §4); 7, 14,
  and 30 days were evaluated unconditionally, with horizon selection
  deferred to the evidence rather than assumed at the outset.
- **Reproducibility** — because a result that cannot be regenerated
  from the same seed is not evidence, it is an anecdote; every stage is
  seed-derived and independently verifiable.
- **Leakage audits** — because a model that discovers a shortcut
  (e.g., a feature that encodes the generator's own ground truth) would
  produce an impressive but meaningless number; column, single-feature,
  and dominance audits ran automatically before any result was
  interpreted (`EVALUATION.md` §3).

Full quantitative detail for every stage above is in `EVALUATION.md`;
this section explains why the experiment was shaped this way, not the
numbers themselves.

---

## 7. Results

**The important research result is not that any single number is
"good."** It is what the *pattern* across horizons, stress conditions,
and scenario types implies for the hypothesis in §5 — and, in several
cases, what it rules out.

**THE PATTERN: separation increases with horizon, and short-horizon
prediction stays weak.**

```
7-day PR-AUC:  0.262
14-day PR-AUC: 0.370
30-day PR-AUC: 0.603
```

This is not simply "30 days is easier because more positives exist" —
the rate of PR-AUC improvement outpaces the modest rise in positive
base rate across the same three horizons (`EVALUATION.md` §5). The
product-design consequence follows directly: **Sentinel should not
pretend to provide a one-week oracle when the current benchmark
supports a longer warning horizon far more strongly.** This is exactly
why the product's saved, deployed artifact is the 30-day model — not a
7-day one — and why the 7-day/14-day results are reported as evaluated-
but-not-deployed rather than hidden.

**THE STRESS TEST: the strongest model degrades the most under drift.**

```
30-day PR-AUC, normal test:  0.603
30-day PR-AUC, temporal stress test: 0.476
```

The candidate that wins on the normal test — the **provisional
benchmark candidate**, a Random Forest at the 30-day horizon — is also
the one that loses the most ground (a 21% relative PR-AUC drop) when
evaluated on a later time period it never trained on. This should be
read as a real limitation of the current candidate under distribution
shift, not a footnote: it stays clearly above the random baseline, but
it does not survive drift cleanly.

**THE WARNING LEAD TIME: 7.0 days, and only after a bug was found.**

The signature metric for the "useful warning" claim in §5 is a median
of **7.0 days** of sustained, genuine lead time at the 30-day horizon —
smaller than the horizon itself, achieved through real precision/recall
trade-offs rather than by over-triggering. This number is only
trustworthy because an earlier, wrong version of it was caught and
corrected — see §8.

**THE ASSUMPTION: "growth might look like risk" — partially survived.**

Pooled across the benchmark, benign-growth windows show GMV rising
~80% on average while chargeback/refund rates stay within roughly ±10%
of baseline; risk windows show GMV rising only ~15% while chargeback
rates rise ~47% (`EVALUATION.md` §9). In aggregate, the model does not
confuse the two. At the individual-scenario level, this is not a clean
result: one hard-negative type (`payment_method_shift`) shows a 0%
false-positive rate — exactly the intended behavior — while another
(`viral_campaign`) shows a 100% false-positive rate, on a small sample
of 7 negative-labeled rows. **This is reported as a genuine, partial
failure of the growth≠risk claim, not smoothed into "mostly works."**

**THE NEGATIVE RESULT: calibration did not help.**

```
Uncalibrated Brier score: ≈0.188
Calibrated (sigmoid) Brier score: ≈0.192
```

A dedicated attempt to calibrate the selected model's probabilities
made the Brier score slightly *worse*, not better — and worse by a
larger margin under temporal stress than on the normal test
(`EVALUATION.md` §6). Discrimination metrics (precision, recall, F1,
PR-AUC) are mathematically unchanged by construction, since sigmoid
scaling cannot alter ranking. This is reported as a negative result: the
model's probabilities, calibrated or not, should be read as directionally
useful for ranking risk, not as literal well-calibrated probabilities.

**Explainability, simulator, and intervention behavior** all passed
their structural verification — SHAP attributions reconstruct the
model's own output to within machine precision (`EVALUATION.md` §10);
the simulator is deterministic, isolated, and never mutates shared
state (§12); intervention recommendations are grounded in the same
verified deviation and SHAP signals, never invented (§13). None of
these results extend to a causal or real-world claim, and the product
language is deliberately built never to imply one.

**Confidence/data-quality** behaves as designed but, in the current
static benchmark (every merchant shares the same observed start date),
varies meaningfully only along the date axis, not the merchant axis, at
a single fixed query — a real, disclosed limitation of what this
specific benchmark can demonstrate about the signal's value
(`EVALUATION.md` §11).

**AI grounding** was independently verified rather than assumed: every
number the assistant cites is proven byte-identical to the same
authoritative service call every other screen uses, and the
prompt-injection pre-filter was tested against both attack phrasings
and legitimate look-alike questions (`EVALUATION.md` §15).

**The cautious research conclusion, stated plainly**: the synthetic
benchmark supports the *feasibility* of the proposed workflow and
provides reproducible, checkable evidence for the methodology behind
each stage. **It does not establish production performance on real
merchant data**, and no result in this section should be read as though
it did.

---

## 8. Failure Analysis

Sentinel's research process treats a discovered failure as a research
result, not something to minimize. This section is given comparable
weight to §7 deliberately.

### THE FAILURE: "30 days was too good to be true."

**What failed.** The first implementation of the project's own
signature metric — median warning lead time — searched for *any*
positive prediction anywhere in the lookback window before a risk
episode, without requiring that positive prediction to be contiguous
with the episode's actual onset.

**Why it mattered.** For a wide lookback window, this trivially credits
the window's *start* by chance — some positive day is likely to exist
somewhere in a long window regardless of genuine, continuous early
detection. The practical effect: the metric reported a median lead time
equal to the horizon's own maximum for nearly every model. For the
eventual selected candidate at 30 days, this initially read as **30.0
days** — a number indistinguishable, on its face, from "the model is
always positive," not genuine early detection.

**How it was discovered.** By checking the metric's own definition
against what it was supposed to measure — sustained early warning
connected to a real episode — rather than accepting a suspiciously
clean, maximal number.

**What changed.** The metric was redefined to require a *sustained*,
contiguous run of positive predictions connecting directly back to the
episode's onset day, stopping at the first negative day encountered
walking backward. An isolated early "blip" with no connection to the
actual onset no longer counts. A regression test locks this behavior in.

**What the corrected result showed.** The selected model's 30-day
median lead time dropped from 30.0 to **7.0 days**.

**Why the less favorable number was kept.** Reporting 30.0 days would
have overstated the model's real early-warning capability by a wide
margin — the difference between "gives a merchant a month's genuine
notice" and "is positive often enough that some day in a 30-day window
happens to be positive." Retaining 7.0 days as the reported result,
even though materially weaker, is the direct application of this
project's stated engineering philosophy: do not fabricate or flatter a
metric. 7.0 days is the number used throughout `EVALUATION.md` and this
document.

### The structurally suppressed archetype

**What failed.** One merchant archetype's original parameter ranges,
combined with a shared business-tier multiplier, could produce
near-zero transaction volume for some merchants — making chargeback
outcomes essentially unobservable regardless of injected risk severity.

**Why it mattered.** That archetype's positive label rate was pinned to
the lowest of all eight archetypes by a wide margin — not because it
was genuinely low-risk, but because its transaction volume was too low
for a chargeback outcome to be observable at all.

**How it was discovered.** Dataset validation's archetype positive-rate
audit, root-caused with a Monte Carlo analysis over the sampling
distribution.

**What changed.** Transaction *volume* parameters were corrected;
chargeback and refund rate ranges were deliberately left untouched, so
the fix could not be mistaken for making the archetype "look" more or
less risky by construction.

**What the corrected result showed.** Previously-silent severe risk
events for that archetype began producing observable outcomes, and its
positive-rate rank moved from lowest-of-eight to mid-pack.

### The temporal distribution-shift result

**What failed** (in the sense of "did not hold up," not "was a coding
bug"): the strongest normal-test candidate degrades the most under a
genuine, never-trained-on later time window.

**Why it mattered.** A model that only performs well on data from the
period it trained on says little about surviving real time passing.

**What the evidence showed.** PR-AUC dropped from 0.603 to 0.476 (a 21%
relative decline) at the 30-day horizon (`EVALUATION.md` §7) — reported
as a real, unresolved limitation, not glossed over.

### The viral-campaign hard-negative failure

**What failed.** One of the four benign-growth hard-negative scenario
types showed a **100% false-positive rate** among its negative-labeled
rows.

**Why it mattered.** This is close to the exact failure mode C6 (§4)
warned would be commercially dangerous — a healthy-growth scenario
being mistaken for risk.

**What remains unknown.** The sample is small (n=7 negative-labeled
rows) — large enough to report honestly, not large enough to draw a
confident conclusion about the underlying cause. Not resolved in this
research pass.

### The calibration negative result

Covered in §7 above. Restated here because it belongs in this section
on principle: a deliberate, evaluated attempt at improvement that did
not succeed, reported as a failure rather than reframed as a partial
win.

### Exposure regression losing to a trivial baseline

**What failed.** A Random Forest regression candidate for future
chargeback exposure amount was beaten on MAE and RMSE by a naive
trailing-average persistence baseline at 14 and 30 days, and even at 7
days where it edges out on MAE, it loses on RMSE.

**Why it mattered.** No regression artifact was worth shipping as a
result — the product's exposure figure uses the same trailing-average
baseline directly, labeled `derived`, rather than presenting a model
output that does not add value over a trivial forecast
(`EVALUATION.md` §17.7).

### The unresolved SHAP finding

**What failed to resolve**, not a bug: in the two highest-confidence
positive predictions individually inspected, a chargeback-rate feature
value of exactly 0.0 (no chargebacks in the trailing window) pushed the
model's score *higher*, opposite to that same feature's global average
signed direction. This is a real, flagged, open question about model
behavior, not root-caused in this research pass (`EVALUATION.md` §10).

### What is deliberately excluded from this section

Ordinary implementation bugs — frontend layout issues, test-selector
ambiguities, styling regressions fixed during development — are normal
engineering work, not research findings, and are not elevated here. The
purpose of this section is to show the team actively tried to break its
own results before reporting them, and changed the reported number when
it found a real problem — not to inflate the list with routine
debugging.

---

## 9. Intervention

The research progression that produced this layer:

```
prediction → explanation → financial consequence → simulation → intervention → response
```

**The research question**: *if Sentinel detects risk early enough, can
observable risk drivers be translated into bounded operational controls
a merchant can actually test?*

This follows directly from falsification concerns C4 and C5 (§4):
prediction alone risks becoming another dashboard a merchant checks
once and ignores. A number that never connects to an action a merchant
can take is not decision intelligence, however accurate it is.

**Current V1 intervention architecture, implemented:**

```
observable merchant signal
    → deterministic intervention rule
    → ranked recommendation
    → existing simulator
    → modeled impact
```

The only controls that currently exist are the simulator's own three:
**refund rate, on-time fulfillment rate, and new-customer share** —
each a real, trailing operational metric the merchant's own data
already contains, not an invented transaction-level object. A control
is only surfaced when its deviation from that merchant's own recent
baseline crosses an empirically chosen threshold, and priority is only
elevated when the same behavior area is independently corroborated by
the model's current SHAP explanation (`EVALUATION.md` §13).

**This is explicitly a deterministic V1 heuristic, not a learned
intervention policy and not an AI-generated suggestion.** The simulator
remains the sole, authoritative source of any counterfactual number —
Intervention Intelligence never computes, caches, or approximates a
modeled-impact figure itself. The system is built throughout to avoid
causal or guaranteed language about what acting on a recommendation
would actually do, enforced by automated forbidden-language tests
(`EVALUATION.md` §13).

---

## 10. Risk Memory / Outcome Loop

Rather than describe this as a finished feature, it is more honest to
frame it as the open research question it actually is:

> **Can observed intervention outcomes eventually improve future
> intervention prioritization?**

**Currently implemented:**

```
recommendation → merchant action → server-rerun simulation → stored record
```

Every step through "stored record" is real: an action is recorded, the
simulation attached to it is independently re-run server-side (never
trusted from the client), and the record is stored per merchant.

**Currently missing**: **real observed outcome.** The public synthetic
benchmark has no mechanism to observe what actually happens to a
merchant after an intervention. As a result, `outcome_status` is
hardcoded to **`not_observed`** for every record this system can ever
produce, and no field, parameter, or code path can set it to anything
else (`EVALUATION.md` §13).

**Sentinel does not claim to have a validated, self-learning
intervention loop.** What exists is the data model and architecture
such a loop would need — a deliberate, stated scope decision (directly
answering C10, §4), not a partial or disguised version of the real
thing.

**The future research loop this architecture is built to eventually
support:**

```
real merchant data → risk detection → intervention → merchant action
    → observed outcome → Risk Memory → intervention effectiveness → improved prioritization
```

This is stated here explicitly as a future research direction that
**requires real-world validation Sentinel does not currently have** —
not a roadmap commitment and not a description of current behavior.

---

## 11. Open Research Questions

These are not framed as a product roadmap. Each is a genuine unresolved
question this research raised but could not answer with the current
benchmark, and each names what evidence would actually be needed.

- **Does the signal generalize to real merchant data?** Nothing in this
  research establishes this either way — it is the single largest gap
  between what was evaluated and what would need to be true for
  production use. *Requires*: real, labeled merchant transaction
  history, which this project does not have access to.
- **Does the 7-day median warning lead time survive real deployment?**
  The synthetic-benchmark figure is a measured, corrected result — not
  a guarantee it transfers to real merchant behavior patterns.
  *Requires*: real deployment with real, later-observed episodes.
- **Does the 30-day horizon remain optimal at larger scale?** The
  horizon comparison in §7 is a property of this specific 50×180
  benchmark and its specific feature set. *Requires*: evaluation at the
  planned ~500×365 benchmark expansion, or real data.
- **How does performance vary by merchant archetype at a defensible
  sample size?** The current test set has roughly one merchant per
  archetype — archetype-level disparities observed in `EVALUATION.md`
  §9 could be genuine archetype effects or single-merchant noise, and
  cannot be separated at n=8. *Requires*: many more test merchants per
  archetype.
- **Does the model maintain separation under stronger distribution
  shift?** Only one stress-test cutoff (day_index ≥ 120) was tried.
  *Requires*: testing at multiple cutoffs and, eventually, real
  multi-year data.
- **Can calibration become useful with more data?** The current
  validation set for calibration fitting is 600 rows — plausibly too
  small for a stable calibration map. *Requires*: a materially larger
  validation set.
- **Can intervention effects be estimated causally, rather than only
  described as a bounded model what-if?** The simulator answers "what
  does the same classifier say under a different input," not "what
  would actually happen." *Requires*: real intervention/outcome data
  and a causal-inference design this project has not attempted.
- **Which of the three current interventions (refund rate, fulfillment,
  customer mix) actually reduces real-world risk, if any?** Entirely
  unanswered — no outcome data exists to test this.
- **Does Risk Memory improve prioritization once real outcomes exist?**
  The entire premise of §10's future loop, untestable until real
  outcome data exists.
- **What happens when merchants have sparse trailing history?** The
  current benchmark gives every merchant a full, uninterrupted history
  from a fixed start date — cold-start and partial-history merchants
  are not represented at all (`docs/architecture/data_generation.md`).
- **How does performance change across business categories not
  represented in the current 8 archetypes?** Untested — the benchmark's
  archetype set, while broad, is not exhaustive of real merchant
  categories.
- **Can settlement-hold or liquidity-survivability scenarios become a
  predictive target in their own right?** Purely conceptual (§3,
  candidate 9) — no experiment has been designed for this.
- **Can merchant continuity intelligence extend meaningfully beyond
  chargeback risk?** An open strategic question, not a research finding
  — see §12.

---

## Research → Product

**Sentinel is not just a chargeback predictor.**

```
QUESTION → RESEARCH → FALSIFICATION → HYPOTHESIS → EXPERIMENT → EVIDENCE → PRODUCT THESIS
```

Each product layer exists because of a specific research conclusion or
an explicitly unresolved problem from the sections above, not because
it seemed like a reasonable feature to add:

- **Risk prediction** exists because §5's first claim needed a model to
  test it against — the entire research program has nothing to falsify
  or support without it.
- **Explainability** exists because a probability with no reason
  attached fails C4 (§4) — a number a merchant cannot interrogate is
  exactly the "dashboard nobody trusts" failure mode.
- **Exposure / liquidity** exists because §1's original reframing was
  explicitly about financial consequence, not a probability in
  isolation.
- **Simulation** exists because C4/C5 (§4) demanded prediction become a
  decision tool, and because C9 demanded that tool be honestly bounded,
  never causal.
- **Intervention Intelligence** exists because C5 demanded prediction
  connect to something a merchant can actually change (§9).
- **Incident response and evidence readiness** exist because §1's
  question explicitly included "prepare before the situation becomes an
  unavoidable loss" — the loop does not stop at prevention.
- **Risk Memory** exists because C10 (§4) demanded that any future
  learning claim be structurally incapable of being faked — so the
  architecture for it was built now, honestly incomplete, rather than
  either omitted or overclaimed (§10).

This is the product thesis that survived the research process described
in this document — not the one the project started with, and not one
assumed in advance. `PRODUCT.md` documents what this thesis looks like
as a working system today; `EVALUATION.md` documents the evidence behind
it; `ARCHITECTURE.md` documents how it is built.

---

## Research → Research Lab

This research journey will also be presented visually, as a section
inside Sentinel's marketing site — the **Research Lab**. It is a
section of the marketing site, not a separate product or a separate
body of findings from this document.

Its planned narrative sequence mirrors this document's structure
directly:

```
Question → Landscape → Candidate Gaps → Falsification → Hypothesis
    → Experiment → Results → Failure Analysis → Intervention → Future
```

presented as a concise, cinematic story — the visual telling of the
same journey, not a different or more favorable one.

**This written document is the source of truth.** The marketing site
visualizes this research; it must not invent claims absent from
`RESEARCH.md` or `EVALUATION.md`. To be explicit about what each
document is for:

- **`RESEARCH.md`** (this document) — the narrative research record.
- **`EVALUATION.md`** — the quantitative evidence.
- **`ARCHITECTURE.md`** — the implementation.
- **`PRODUCT.md`** — current product behavior.

At the end of the marketing website, the planned destinations are the
GitHub repository, the pitch video, and the deployed Sentinel product —
the live product link to be added once deployment exists.

---

## Sources

Every source below was consulted directly during the writing of this
document. Where a claim in this document draws on project reasoning
rather than an external source, it is labeled as such in the text
above and is not listed here.

### Payments / Disputes

- **"About Disputes."** Razorpay. Official product documentation.
  <https://razorpay.com/docs/payments/disputes/> — Supports: the
  definition of a dispute, the merchant accept/contest lifecycle, and
  the "phases" a dispute moves through (§1, §2).
- **"The Ultimate Guide to Chargeback Reason Codes."** Razorpay Blog.
  <https://razorpay.com/blog/chargeback-reason-codes/> — Supports:
  chargeback reason-code structure across Visa/Mastercard/Amex/
  Discover, and the claim that networks monitor chargeback rates by
  reason code and can fine or restrict merchants who exceed thresholds
  (§2).
- **"Disputes."** Stripe Documentation.
  <https://docs.stripe.com/disputes> — Supports: the definition of a
  dispute/chargeback, how a chargeback reverses a payment and debits
  the merchant, and the evidence-response workflow (§2).
- **"Measuring disputes."** Stripe Documentation.
  <https://docs.stripe.com/disputes/measuring> — Supports: the claim
  that the credit-card-processing industry treats dispute activity
  above **0.75%** as excessive, and the existence of card-network
  dispute/fraud monitoring programs (e.g. Visa's VAMP) (§2).
- **"Dispute prevention."** Stripe Documentation.
  <https://docs.stripe.com/disputes/prevention-preview> — Supports:
  the description of Verifi/Ethoca-style pre-dispute alerting,
  "Compelling Evidence" dispute-blocking, and Stripe's automated
  "Smart Disputes" evidence-submission tooling (§2).
- **"Manage disputes."** Adyen Docs.
  <https://docs.adyen.com/risk-management/manage-disputes/> —
  Supports: merchant dispute-defense material requirements, and the
  description of Adyen's RevenueProtect ML-and-rules risk system (§2).
- **"Dispute Management Guidelines for Visa Merchants."** Visa, June
  2024. <https://usa.visa.com/dam/VCOM/global/support-legal/documents/merchants-dispute-management-guidelines.pdf>
  — Supports: the existence of Visa Claims Resolution's Allocation/
  Collaboration workflow structure and Visa's stated dispute time
  limits (120 days standard; longer for specific categories) (§2, §3).
  *Note: this PDF could not be rendered as plain text by this
  session's fetch tool; the facts cited from it are corroborated by the
  document's indexed content returned via search and by independent
  secondary summaries, not by a direct full-text read in this session.*
- **"Chargebacks Made Simple Guide."** Mastercard.
  <https://www.mastercard.us/content/dam/public/mastercardcom/na/global-site/documents/chargebacks-made-simple-guide.pdf>
  — Supports: the existence and general shape of Mastercard's
  chargeback lifecycle (first chargeback, presentment, arbitration).
  *Same fetch-tool limitation as above — cited for its documented
  existence and title, not a verified full-text quotation.*
- **"Visa Agrees to Buy Verifi As Payments Players Wrestle With Rising
  Chargebacks."** Digital Transactions, 2019.
  <https://www.digitaltransactions.net/visa-agrees-to-buy-verifi-as-payments-players-wrestle-with-rising-chargebacks/>
  — Supports: Visa's 2019 acquisition of Verifi and Mastercard's prior
  acquisition of Ethoca, as evidence that pre-dispute alerting is
  established, network-owned infrastructure (§2).

### Risk / Fraud

- **"Manage disputes"** (Adyen, cited above) — Supports: RevenueProtect
  as an example of transaction-level ML-plus-rules fraud/risk
  decisioning, used in §2's landscape layering.
- **Tiwari, P., Mehta, S., Sakhuja, N., Kumar, J., & Singh, A. K.
  "Credit Card Fraud Detection using Machine Learning: A Study."**
  arXiv:2108.10005, submitted August 23, 2021.
  <https://arxiv.org/abs/2108.10005> — Supports: that machine-learning
  approaches to transaction-level fraud detection are an active,
  published academic research area, used to ground §2's transaction-
  decisioning layer as real, mature infrastructure rather than an
  assumption.

### Merchant Economics

- **Hayashi, F., Markiewicz, Z., & Sullivan, R. J. "Chargebacks:
  Another Payment Card Acceptance Cost for Merchants."** Federal
  Reserve Bank of Kansas City, Research Working Paper RWP 16-01, 2016.
  <https://www.kansascityfed.org/research/research-working-papers/chargebacks-payment-card-cost-merchants-2016/>
  — Supports: that merchants bear roughly 70–80% of chargeback losses
  as merchant-liable outcomes, that fraud accounts for roughly half of
  all chargebacks, and reported chargeback rates in basis points of
  sales number/value (§1, §4-C1). *Note: this session's fetch tool
  could not retrieve the paper's full text (HTTP 403); the specific
  figures cited are drawn from this paper's findings as reported
  consistently across the paper's own abstract/summary content
  returned via search, not from an in-session full-text read.*
- **LexisNexis Risk Solutions. "True Cost of Fraud™ Study" (2026
  release).**
  <https://risk.lexisnexis.com/about-us/press-room/press-release/20260624-tcof-retail-and-commerce>
  — Supports: that the total cost of fraud to U.S./Canadian retail and
  e-commerce businesses is estimated at roughly $5 in total cost for
  every $1 of direct fraud loss, used as external evidence that fraud-
  and-dispute-related costs extend materially beyond the disputed
  transaction amount itself (§1).

### Regulatory / Industry

- **Reserve Bank of India. "Harmonisation of Turn Around Time (TAT)
  and customer compensation for failed transactions using authorised
  Payment Systems."** Notification, effective October 15, 2019.
  <https://www.rbi.org.in/commonman/English/scripts/Notification.aspx?Id=3074>
  — Supports: the exact regulatory timelines (T+1 day for UPI/IMPS-
  class transfers; T+5 days for card and e-commerce transactions) and
  the ₹100-per-day compensation rule for failed/delayed transaction
  resolution in India, used as evidence that timely resolution in
  payments carries direct regulatory weight (§2).
- **"Streamlining Dispute Resolution for Digital Transactions: All you
  need to know about NPCI-Led UDIR."** Razorpay Blog.
  <https://razorpay.com/blog/all-you-need-to-know-about-npci-led-udir/>
  — Supports: the existence and general design of NPCI's Unified
  Dispute and Issue Resolution (UDIR) platform for UPI (launched 2020,
  automated API-based complaint/dispute handling). *This is a secondary
  explainer of an NPCI-operated system, not NPCI's own primary
  publication — NPCI's own site was not directly retrievable by this
  session's fetch tool.*
- **"Visa Agrees to Buy Verifi..."** (Digital Transactions, cited above
  under Payments/Disputes) — also supports the regulatory/industry
  context of network-level consolidation around dispute infrastructure.

### Academic / Research

- **Tiwari et al., arXiv:2108.10005** (cited above under Risk/Fraud).
- **Hayashi, Markiewicz & Sullivan, Federal Reserve Bank of Kansas
  City RWP 16-01, 2016** (cited above under Merchant Economics) — a
  central-bank research working paper, included here as the project's
  primary academic-quality source on merchant-side chargeback
  economics.
- **"Prediction of Credit Card Chargebacks in the Live Events Ticketing
  Industry Using Machine Learning Algorithms."** eScholarship
  (University of California).
  <https://escholarship.org/uc/item/28q5c42d> — Supports: that
  chargeback prediction specifically (not only transaction-level fraud
  detection) is an existing, published academic research direction, in
  a different domain (ticketing) than this project's payments-benchmark
  context. *This session's fetch tool could not retrieve the paper's
  full text; it is cited for its confirmed title, venue, and existence
  via the eScholarship repository, not for a verified detailed finding.*
