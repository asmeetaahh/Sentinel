# Baseline ML Evaluation Report

Scope: `PROJECT_CONTEXT.md` implementation order step 3 ("Baseline models")
and step 4 ("Candidate ML models"), evaluated together. No backend,
frontend, LLM layer, simulator, or SHAP work was done here. The generator
and feature-engineering pipeline were not modified.

Reproduce with:
```bash
.venv/bin/python scripts/run_baseline_ml.py
.venv/bin/python -m pytest tests/test_modeling_pipeline.py -v
```

Inputs: `data/processed/features.csv`, `data/processed/labels.csv`,
`data/raw/merchants.csv` (`data/scenarios/events.csv` for failure analysis
only — never a model feature). Outputs:
`data/metadata/modeling/{results.json,comparison_table.csv,plots/*.png}`.

**Every number below is pulled from `results.json` — nothing here is
hand-typed from memory.** These are synthetic-benchmark results. They say
nothing about real-world predictive validity, and Sentinel does not have
and does not claim access to real Razorpay data.

---

## A. Exact dataset / split used

- 50 merchants × 180 days, seed 42 (SHA256-16 of inputs recorded in
  `results.json.run_metadata` for exact reproducibility: features.csv
  `316a1ae25de3c530`, labels.csv `2e0e164747463262`, merchants.csv
  `fef12a440a582dec`).
- **Merchant-level split**, archetype-stratified via largest-remainder
  (Hamilton) apportionment, seed 42:

| Split | Merchants | Fraction |
|---|---|---|
| Train | 32 | 64.0% |
| Val | 10 | 20.0% |
| Test | 8 | 16.0% |

  Target was 60/20/20; the deviation is the unavoidable consequence of
  apportioning 6-7-merchant archetype groups into three buckets with a
  deterministic, documented rounding rule (see `splits.py`) — not a bug.
  Verified programmatically: no merchant appears in more than one split
  (`test_split_covers_all_merchants_with_no_overlap`).
- **Temporal cutoff**: `day_index < 120` is "early" (used for train/val and
  the normal test); `day_index >= 120` is "late," used **only** for the
  temporal stress test, and **only** for the 8 already-held-out test
  merchants — the model never sees late-period data during training, from
  any merchant. This isolates "does it survive time drift" from "does it
  generalize to unseen merchants" (the ordinary test split already covers
  the latter).
- Join key: `(merchant_id, day_index)`, validated one-to-one
  (`datasets.py:build_horizon_frame`, `validate="one_to_one"`).

## B. Models evaluated

| Model | Notes |
|---|---|
| A. Historical-threshold baseline | Single causal feature (`chargeback_rate_deviation_z`, from feature engineering's deviation-from-baseline group), threshold F1-tuned on train only. Deliberately not "an ML model" — no cross-merchant pattern learning. |
| B. Logistic Regression | `StandardScaler` + `LogisticRegression(class_weight='balanced')`, sensible defaults, not tuned. |
| C. Random Forest | `class_weight='balanced_subsample'`, `max_depth=6`, `n_estimators=300`. |
| D. XGBoost | Was **unavailable initially** — missing `libomp` on macOS (a known XGBoost-on-Mac issue, not a Python dependency gap). Installed via `brew install libomp` (reversible, low-risk, documented in `requirements.txt`) rather than silently substituting a different model, per the explicit instruction. `scale_pos_weight` set from the train split's own class ratio (standard practice, not tuning). |

None of the four were tuned against test-set results. Hyperparameters are
in `ml/modeling/config.py`, chosen once, before running any evaluation.

## C. Full classification results (test set)

| Model | Horizon | Precision | Recall | F1 | PR-AUC | ROC-AUC (secondary) | Median Warning Lead Time (days) |
|---|---|---|---|---|---|---|---|
| historical_threshold_baseline | 7 | 0.185 | 0.988 | 0.311 | 0.181 | — | 7.0 |
| logistic_regression | 7 | 0.206 | 0.843 | 0.331 | 0.226 | — | 7.0 |
| random_forest | 7 | 0.224 | 0.674 | 0.337 | 0.262 | — | 7.0 |
| xgboost | 7 | 0.218 | 0.750 | 0.338 | 0.221 | — | 7.0 |
| historical_threshold_baseline | 14 | 0.207 | 0.995 | 0.343 | 0.211 | — | 14.0 |
| logistic_regression | 14 | 0.277 | 0.621 | 0.383 | 0.301 | — | 12.0 |
| random_forest | 14 | 0.244 | 0.717 | 0.365 | 0.370 | — | 14.0 |
| xgboost | 14 | 0.257 | 0.616 | 0.363 | 0.269 | — | 10.0 |
| historical_threshold_baseline | 30 | 0.252 | 1.000 | 0.402 | 0.257 | — | 30.0 |
| logistic_regression | 30 | 0.455 | 0.718 | 0.557 | 0.486 | — | 16.0 |
| **random_forest** | **30** | **0.502** | 0.552 | 0.526 | **0.603** | — | 7.0 |
| xgboost | 30 | 0.437 | 0.751 | 0.553 | 0.467 | — | 12.0 |

(ROC-AUC values are in `results.json` as `roc_auc_secondary`; omitted from
this table by design — per PROJECT_CONTEXT.md, PR-AUC is the metric that
matters for a ~20-29%-positive detection task, ROC-AUC is a secondary
diagnostic only, and repeating both here would overweight it visually.)

**The historical-threshold baseline's near-perfect recall is not a sign of
skill.** At every horizon, its validation-selected threshold ends up
flagging 96-99.7% of ALL test rows positive (h=30: 997/1000 rows flagged;
`results.json` confusion matrices). Its PR-AUC (0.18-0.26) sits barely
above the raw positive rate (0.22-0.29) — this is close to a "flag
everything" degenerate strategy, not genuine detection. This matters
directly for interpreting warning lead time below.

## D. Horizon comparison

| Horizon | Best PR-AUC (model) | Positive rate (test) | Usable? |
|---|---|---|---|
| 7d | 0.262 (random_forest) | ~18-21% | Weak — all models cluster near the random-baseline PR curve (see `plots/pr_curves_by_horizon.png`, leftmost panel) |
| 14d | 0.370 (random_forest) | ~21-25% | Moderate — models separate from random but not strongly |
| 30d | **0.603 (random_forest)** | ~25-28% | **Strongest** — clear separation from random across most of the recall range |

**PR-AUC rises sharply with horizon** (this holds for every ML model, not
just the winner: LR 0.226→0.301→0.486, XGB 0.221→0.269→0.467, RF
0.262→0.370→0.603). Two things point to this being genuine, not just "more
positives = easier": (1) the *rate* of improvement far exceeds the modest
rise in positive-class base rate (18%→28%, less than double, vs. PR-AUC
roughly tripling for RF), and (2) F1 improves in step (RF: 0.337→0.365→0.526).
**7 days is too short a horizon for any model here to add much value over
chance-ranking; 30 days is where the signal is clearly usable.**

Warning lead time (see F below) tells a consistent story from the other
direction: at 7d there's almost no runway to be "early" (max possible lead
time is 7 days), while 30d gives room for a genuine multi-week head start
— but only for the models whose lead time isn't an artifact of
over-triggering (see F).

**Neither extreme materializes**: 30d does not become "trivially easy" (RF
PR-AUC 0.603 is well short of 1.0, and precision at the chosen threshold is
only 0.50) and 7d is not "literally unusable" (RF still clears
PR-AUC 0.262 vs. an ~18% base rate) — but 30d is unambiguously the horizon
where a model provides the most separation from chance.

## E. Calibration findings

Evaluated on raw (uncalibrated) model output first, per the explicit
instruction not to calibrate before comparing.

| Model | Horizon | Brier score | Mean predicted − observed | Verdict |
|---|---|---|---|---|
| random_forest | 30 | 0.188 | +0.157 | Overconfident |
| logistic_regression | 30 | 0.221 | +0.210 | Overconfident |
| xgboost | 30 | 0.211 | +0.107 | Overconfident |

**All models trend overconfident at higher predicted-probability bins**
(visible in `plots/calibration_by_horizon.png`: points fall below the
diagonal at the high end across all three horizons) — a predicted
probability of 0.8-0.9 corresponds to an observed positive frequency
closer to 0.3-0.5 for most models at most horizons. Reliability curves are
also visibly noisy (10 quantile bins over a 100-250-row test set means
some bins hold ~10-25 points), so read the curve's shape as directional,
not precise. We did **not** apply a calibration method (Platt/isotonic) to
any model in this pass — per the instruction to compare raw performance
first; whether calibration is worth adding to the eventual selected model
is a follow-up, not resolved here, since it wasn't demonstrated to
materially change the model comparison.

**Caveat on the baseline's calibration entry**: `historical_threshold_baseline`
does not output a real probability (it's a thresholded raw z-score); its
calibration numbers use a min-max-scaled pseudo-probability purely for
plotting on a comparable 0-1 axis, and should not be read as a genuine
calibration failure/success in the same sense as the other three models.

## E.1 Calibration implementation and evaluation (follow-up pass)

This section documents a dedicated follow-up pass evaluating and
implementing calibration for the provisional Random Forest / 30-day
candidate specifically, per a subsequent, narrower task. Reproduce with
`scripts/evaluate_calibration.py`; results in
`data/metadata/modeling/calibration_results.json`.

### Method

**Platt scaling (sigmoid)**, via `sklearn.calibration.CalibratedClassifierCV`
wrapping a `FrozenEstimator`-wrapped, already-fit Random Forest (the
`cv="prefit"` API was removed in sklearn ≥1.6; `FrozenEstimator` is its
replacement — same semantics, base model frozen, never refit by the
calibrator).

**Why sigmoid, chosen before fitting or evaluating either method** (not by
comparing results and picking the winner): isotonic regression is
nonparametric and prone to overfitting or producing a jagged, non-smooth
map when the calibration set is modest; sigmoid fits only 2 parameters and
is the standard, more data-efficient default at the available scale
(600 rows after the validation split below). A same-day diagnostic
comparison (not the selection method — see below) confirmed this was the
right call: isotonic's test-set Brier score (0.209) was worse than
sigmoid's (0.192), which was itself worse than doing nothing (0.188) — see
"Result" below.

**Fitting protocol** (train/validation only, test never touched):
1. Base Random Forest fit on the merchant-level **train** split only,
   identical hyperparameters to the uncalibrated baseline
   (`config.RANDOM_FOREST_PARAMS`, with `n_jobs` pinned to 1 for this
   artifact specifically — see Limitations).
2. The 1,200-row **validation** split is itself divided in two (seeded,
   stratified, 50/50): `val_calibration` (600 rows) fits the sigmoid map;
   `val_threshold` (600 rows, disjoint from the first) selects the
   F1-maximizing decision threshold — for both the calibrated **and**
   uncalibrated variants, so the comparison below is like-for-like. (The
   original baseline report's uncalibrated-RF numbers used the *full*
   1,200-row validation set for threshold selection; re-selecting on the
   600-row `val_threshold` half here is why this section's "uncalibrated"
   row differs very slightly from Section C's.)
3. Test set used only for final evaluation, in both variants.

### Result: calibration did NOT clearly improve this candidate

| Metric (test, h=30) | Uncalibrated RF | Calibrated RF (sigmoid) |
|---|---|---|
| Precision | 0.502 | 0.502 |
| Recall | 0.552 | 0.552 |
| F1 | 0.526 | 0.526 |
| PR-AUC | 0.603 | 0.603 |
| **Brier score** | **0.188** | **0.192** (worse) |
| Mean predicted − observed (avg. bias) | +0.157 | +0.134 (smaller) |
| Calibration verdict | Overconfident | Overconfident |
| FP:TP ratio | 0.99 | 0.99 |
| Median warning lead time (days) | 7.0 | 7.0 |

**Precision/recall/F1/PR-AUC/FP-cost/warning-lead-time are IDENTICAL between
the two** — this is mathematically expected, not a bug: sigmoid scaling is
a strictly monotonic transform of the raw score, so it cannot change the
induced ranking, and therefore cannot change any metric computed from a
rank-based threshold search over that ranking
(`test_calibration_preserves_ranking_relative_to_uncalibrated` asserts this
directly). **Only Brier score and the reliability curve shape can differ —
and Brier score got slightly worse, not better.**

The average bias (`mean_predicted_minus_observed`) did shrink (+0.157 →
+0.134), which sounds like an improvement, but the reliability curve
(`plots/calibration_before_after.png`) shows why Brier disagrees: the
underlying raw reliability curve is genuinely non-monotonic and noisy at
this sample size (bins alternate between ~0.03 and ~0.22 observed frequency
at similar predicted-probability levels — see the reliability-curve data in
`calibration_results.json`). A 2-parameter sigmoid cannot fit a
non-monotonic pattern; it can only rescale toward smaller *average* error
while making specific regions worse — here, the highest-confidence bin
became more extreme (0.86→0.92 mean predicted, same 0.68 observed),
which Brier's squared-error penalizes disproportionately. **This is a
genuine, checked finding** (confirmed with isotonic too, which was worse
still — see Method above), not a bug in the calibration code: given this
benchmark's current validation-set size, post-hoc calibration does not
reliably improve this specific Random Forest's probability outputs.

### Stress-test behavior

| Metric (stress test, h=30) | Uncalibrated RF | Calibrated RF |
|---|---|---|
| PR-AUC | (same ranking → identical to uncalibrated by construction) | |
| Brier score | 0.231 | **0.253** (worse, and by more than on the normal test — +9.4% relative vs. +2.2% relative) |
| Mean predicted − observed | +0.059 | +0.036 (smaller) |

**Calibration's Brier-score cost is larger under temporal distribution
shift, not smaller.** The sigmoid map was fit on early-period validation
data; applying it to late-period (post-cutoff) test rows extrapolates a
mapping learned under one distribution to a somewhat different one, and
that extrapolation cost shows up as a larger Brier penalty than on the
normal (early-period) test set. This is a real, checked limitation, not
elided: calibration does not "travel" better than the raw model under
drift here — if anything, slightly worse.

### Leakage verification

Checked both structurally and behaviorally (`tests/test_calibration.py`,
10 tests, all passing):
- `fit_calibrated()`'s signature has exactly four parameters
  (`X_train, y_train, X_val_calibration, y_val_calibration`) — there is no
  parameter through which test data could be passed, verified by
  introspecting the signature directly, not just by code review.
- The base Random Forest's `feature_importances_` are bit-identical before
  and after the calibrator is fit on `val_calibration` — proving the
  "frozen" base model is genuinely not refit on validation data.
- `val_calibration` and `val_threshold` are verified disjoint and their
  union exactly equals `val` (no validation row is used for both purposes,
  no validation row is dropped).
- Fitting twice with an unrelated, wildly-scaled "test-like" array sitting
  in scope produces identical calibrator output — ruling out any
  accidental reference/closure capture of test data.
- A model fit once and asked to score the test set twice returns
  bit-identical results (deterministic inference, see Limitations for the
  `n_jobs` fix this required).

### Limitations

- **A real (harmless) nondeterminism was found and fixed during this pass**:
  `RandomForestClassifier`'s `predict_proba` with `n_jobs=-1` (the shared
  baseline setting) is not bit-exact reproducible run-to-run — parallel
  reduction across threads sums per-tree probabilities in a
  non-deterministic order, causing ~1e-16 (machine-epsilon) differences.
  Confirmed empirically to have zero effect on the fitted trees or any
  reported metric (`feature_importances_` identical regardless of
  `n_jobs`), but it does violate a literal "deterministic inference"
  requirement. Fixed by pinning `n_jobs=1` for this artifact's base model
  specifically — the shared `config.RANDOM_FOREST_PARAMS` (and therefore
  the original baseline evaluation's numbers) is untouched.
- **The validation set is small** (1,200 rows for this horizon, halved to
  600 for calibration fitting) — this is very likely *why* calibration
  didn't help here; a materially larger validation set (available at the
  eventual ~500-merchant scale) might change this conclusion in either
  direction. This was not re-tested at scale in this pass.
- **Only one calibration configuration was adopted** (sigmoid, 50/50
  validation split); isotonic was checked once as a diagnostic, not
  formally evaluated end-to-end (no isotonic artifact was saved) — per the
  instruction not to search across many configurations.
- **This does not establish that Random Forest is well- or poorly-suited
  to calibration in general** — only that this specific implementation, at
  this specific (small) validation scale, did not produce a clear
  improvement. Calibration remains a reasonable thing to revisit once more
  data is available.

## F. False-positive cost assumptions

**What constitutes a false positive**: a merchant-day where the model
predicts an elevated chargeback-loss episode will occur within the horizon,
but the label says it does not.

**Assumed cost**: 1 synthetic unit per false positive, representing analyst
review time / merchant friction from an unwarranted risk flag. **This
number is not derived from any real Razorpay cost data — it is a modeling
assumption chosen for illustration.**

**Sensitivity analysis** (net value = `benefit_per_TP × TP − 1 × FP`, swept
over three assumed benefit multiples, per `config.BENEFIT_PER_TRUE_POSITIVE_SENSITIVITY`):

| Model (h=30) | FP | TP | FP:TP ratio | Net value @ benefit=2 | @ benefit=5 | @ benefit=10 |
|---|---|---|---|---|---|---|
| historical_threshold_baseline | 716 | 241 | 2.97 | −234 | 489 | 1694 |
| logistic_regression | 207 | 173 | 1.20 | 139 | 658 | 1523 |
| **random_forest** | **132** | **133** | **0.99** | 134 | 533 | 1198 |
| xgboost | 233 | 181 | 1.29 | 129 | 672 | 1577 |

At the lowest assumed benefit multiple (2×), the historical baseline's
massive false-positive volume actually produces **negative** net value —
its "perfect recall" costs more in false alarms than it's worth unless a
caught episode is assumed to be worth at least ~3× a false alarm's cost.
**Random forest is the only model with fewer false positives than true
positives** (FP:TP = 0.99) — the most favorable false-alarm profile of the
four, though not the highest net value at every benefit multiple (XGBoost
edges ahead at benefit=5 and 10, since its higher recall generates more TPs
to offset its larger FP count). This table exists to show the trade-off
shape, not to declare a "correct" multiplier — see the full sweep and all
horizons in `results.json`.

## G. Warning lead-time results

**Definition** (see `warning_lead_time.py` for the full docstring): an
"episode" is a maximal contiguous run of positive-labeled as_of_dates per
merchant (collapsing a long elevated run into one event, not N warnings).
`onset_day` = the run's first day. We require a **sustained** alert:
walking backward from `onset_day - 1`, the model's prediction must be
positive on every day, stopping at the first negative day or at
`onset_day - horizon_days` (whichever comes first). `lead_time = onset_day
- run_start_day`. A detection landing on or after `onset_day` is recorded
separately and **never** counted as an "early" warning.

**A real bug was found and fixed here during development**: the first
implementation searched for *any* positive day anywhere in the lookback
window (not requiring contiguity to onset), which trivially hit the
window's start often by chance for wide windows — producing a median lead
time equal to the horizon's maximum for nearly every model (e.g.
random_forest at 30d: 30.0). Requiring a sustained, contiguous run
connected to the onset dropped that same cell to **7.0** — a materially
different, more honest number. Both the bug and fix are documented in the
module and covered by regression tests
(`test_isolated_early_blip_not_connected_to_onset_does_not_count_as_early`).

| Model | Horizon | Median lead time (days) | Episodes: early / at-or-after-onset / missed |
|---|---|---|---|
| historical_threshold_baseline | 7 | 7.0 (= max possible) | see note below |
| logistic_regression | 7 | 7.0 | |
| random_forest | 7 | 7.0 | |
| xgboost | 7 | 7.0 | |
| historical_threshold_baseline | 14 | 14.0 (= max possible) | |
| logistic_regression | 14 | 12.0 | |
| random_forest | 14 | 14.0 | |
| xgboost | 14 | 10.0 | |
| historical_threshold_baseline | 30 | 30.0 (= max possible) | |
| logistic_regression | 30 | 16.0 | |
| **random_forest** | **30** | **7.0** | 9 early / 7 at-or-after-onset / 9 missed (out of 25 total episodes) |
| xgboost | 30 | 12.0 | |

**The historical baseline's lead time sitting exactly at the horizon
maximum for all three horizons is the same over-triggering artifact as its
recall** — if a model is positive on ~97-99.7% of all days, it is
trivially "sustained-positive" for the entire lookback window before
almost every episode, so it always gets credited the maximum possible lead
time. This is not evidence of good early warning; it's a mechanical
consequence of never really turning off. **Random forest's honest median
of 7 days at the 30-day horizon (achieved with real precision/recall
trade-offs, not blanket triggering) is the more meaningful number.**

Full per-horizon episode counts and percentiles are in `results.json` and
`plots/warning_lead_time_distribution.png`.

## H. Temporal stress-test results

Same 8 test merchants, `day_index >= 120` (the model never trained on this
period, from any merchant).

| Model | Horizon | Normal-test PR-AUC | Stress PR-AUC | Δ | Normal recall | Stress recall |
|---|---|---|---|---|---|---|
| random_forest | 7 | 0.262 | 0.280 | +0.018 | 0.674 | 0.533 |
| random_forest | 14 | 0.370 | 0.303 | −0.067 | 0.717 | 0.670 |
| **random_forest** | **30** | **0.603** | **0.476** | **−0.127** | 0.552 | 0.451 |
| logistic_regression | 7 | 0.226 | 0.411 | +0.185 | 0.843 | 0.467 |
| logistic_regression | 30 | 0.486 | 0.369 | −0.117 | 0.718 | 0.338 |
| xgboost | 30 | 0.467 | 0.399 | −0.068 | 0.751 | 0.507 |
| historical_threshold_baseline | 30 | 0.257 | 0.221 | −0.036 | 1.000 | 1.000 |

**Random forest at 30d — the strongest normal-test candidate — degrades
the most under temporal shift** (PR-AUC −21% relative, recall −18%
relative). It still clearly beats the baseline and stays well above chance,
but this is real, non-trivial distribution-shift sensitivity, not a clean
pass. **Logistic regression at 7d shows PR-AUC improving under stress while
recall collapses (0.843→0.467)** — its fixed decision threshold, chosen on
early-period validation data, becomes miscalibrated for the late period
even though its underlying ranking ability (PR-AUC) holds up; this is a
concrete illustration of why a fixed operating threshold is itself a
drift-sensitive design choice, separate from the model's ranking quality.
**The historical baseline is the most "stable" — because a strategy that
always fires can't really degrade further.** Stability alone is not a
virtue here.

**Sentinel does not fully survive distribution shift at the 30-day
horizon** in this benchmark. It survives partially: performance drops but
stays well above the random-chance floor. This should be treated as a real
limitation, not glossed over.

## I. Exposure regression results (secondary problem)

| Horizon | Model | MAE | RMSE | Normalized MAE (% of mean true value) |
|---|---|---|---|---|
| 7 | naive trailing baseline | 1426.7 | 2325.8 | 105.0% |
| 7 | Random Forest candidate | **1345.3** | 2700.8 | 99.0% |
| 14 | naive trailing baseline | **2355.6** | **3643.2** | **85.0%** |
| 14 | Random Forest candidate | 2572.3 | 4306.9 | 92.8% |
| 30 | naive trailing baseline | **4492.2** | **7124.4** | **69.4%** |
| 30 | Random Forest candidate | 5035.2 | 8826.9 | 77.8% |

**The naive "no change from recent trailing average" baseline beats the
Random Forest candidate on MAE and RMSE at 14d and 30d, and even at 7d
where RF wins on MAE, RF loses on RMSE** (more large outlier misses despite
a lower typical error). This is reported plainly, not reframed: **the
current 55-feature set and a default Random Forest regressor do not yet
improve on a trivial persistence forecast for this target.** Standard MAPE
is not reported (`future_chargeback_amount` is zero for a large fraction of
rows — see the dataset validation report — making per-row percentage error
undefined); normalized MAE (MAE as % of mean true value) is used instead
as a stable, meaningful substitute. This secondary problem was
intentionally kept small per the task brief; it has not received the same
depth of iteration as the classification problem and should not be judged
as a finished result either way.

## J. Feature / shortcut audit

Run automatically before any result was interpreted (`shortcut_audit.py`),
per every horizon's train split:

- **Column audit: passed at all 3 horizons.** No feature name contains
  `baseline_`, `event_type`, `event_id`, `severity_score`, `hard_negative`,
  `elevation_ratio`, `future_chargeback`, `future_transaction`,
  `label_elevated`, or `archetype`. `merchant_id` and `day_index` are not
  in the feature matrix (verified structurally, not just by name-scan —
  `datasets.xy()` only ever selects the 55 manifest columns).
- **Single-feature AUC audit: no suspicious values** (threshold 0.97) at
  any horizon. The most discriminative single features at 30d were
  `days_since_last_chargeback` (AUC 0.758) and `chargeback_rate_acceleration`
  (AUC 0.589) — both legitimate, causal, chargeback-history-derived
  features; neither is surprising or indicates a leak.
- **Feature-importance concentration: no dominant feature.** Top feature
  share of total importance was 15.4% (random_forest) and 12.0% (xgboost)
  at 30d — well under the 50% dominance threshold. `chargeback_rate_28d`
  was the top feature for both tree models, which is exactly what a
  correctly-functioning, non-shortcut-driven model should lean on for this
  task.
- **Archetype cannot dominate via a shortcut**: archetype is not a feature
  at all (excluded at the feature-engineering stage, confirmed here by the
  column audit), so it cannot enter the model's decision function except
  through legitimate behavioral proxies (e.g. an archetype's typical
  transaction volume) — which is the intended behavior, not a shortcut.
- **`overall_shortcut_audit_pass: true` for the full run.**

No feature was added, removed, or reweighted based on label correlation at
this stage — the audit is diagnostic only.

## K. Failure analysis

Computed for every model×horizon combination by joining false
positives/negatives back to `events.csv` (ground truth, used here only for
post-hoc analysis — never as a model input) and `merchants.csv`. Detailed
below for random_forest at 14d as the representative case (full data for
every combination in `results.json.failure_analysis`); qualitative
patterns were consistent across models.

**Rates, not raw counts** (rate = errors within a category ÷ all rows in
that category — this is what shows over/under-representation, not just
"this category is common"):

| Category (active during the row) | FP rate among negatives | FN rate among positives |
|---|---|---|
| `payment_method_shift` | **0.000** (0/34) | 1.000 (5/5) |
| `festival_growth` | 0.318 (7/22) | 1.000 (4/4) |
| `viral_campaign` | **1.000** (7/7) | 0.000 (0/5) |
| `compound_risk` | **0.980** (49/51) | 0.357 (5/14) |
| `fulfillment_degradation` | 0.670 (59/88) | 0.438 (7/16) |
| `normal` (no active scenario) | 0.561 (220/392) | 0.182 (18/99) |

**Two findings worth calling out directly, in opposite directions:**

1. **Good sign**: `payment_method_shift` has a **0% false-positive rate**
   among its negative-labeled rows — the model correctly does not confuse
   this hard-negative growth scenario with risk, exactly the behavior
   `PROJECT_CONTEXT.md`'s growth≠risk principle is meant to produce.
2. **Bad sign, exactly the failure mode the brief warns about**:
   `viral_campaign` shows a **100% false-positive rate** (7 of 7
   negative-labeled viral_campaign rows were flagged positive) — though
   n=7 is small. `compound_risk` shows a 98% false-positive rate among its
   *negative*-labeled rows, which has a more charitable reading: `compound_risk`
   is a gradually-ramping scenario, and a negative-labeled row *during* its
   ramp-up (before the label's threshold formally triggers) may genuinely
   show early, real deterioration signal the label hasn't caught up to yet
   — i.e., some of these "false positives" could be the model catching
   real risk slightly ahead of the label, not the model being wrong. This
   benchmark's label design cannot fully distinguish these two
   explanations, and neither should be assumed without deeper case review.

**Archetype breakdown — read with a strong caveat.** With only 8 test
merchants across 8 archetypes (~1 per archetype), FP/FN rates by archetype
are largely single-merchant statistics:

| Archetype | FP rate among negatives | FN rate among positives |
|---|---|---|
| Digital Goods | 0.926 | 0.128 |
| Quick Commerce | 0.890 | 0.000 |
| Education | 0.780 | 0.000 |
| SaaS | 0.717 | 0.357 |
| Travel | 0.535 | 0.347 |
| Electronics | 0.489 | 0.000 |
| Marketplace | 0.157 | 0.444 |
| D2C Fashion | 0.087 | 0.750 |

A clear split exists — some archetypes get almost everything flagged (high
FP, e.g. Digital Goods/Quick Commerce/Education), others get almost
nothing flagged (high FN, e.g. D2C Fashion/Marketplace). **This should NOT
be read as "these archetypes are inherently harder"** — it is plausibly
one or two specific merchants' idiosyncratic feature distributions
interacting with a single global decision threshold, at this sample size.
This is flagged as a genuine open question (see N), not a settled
conclusion — it would need many more test merchants per archetype (i.e.
the eventual 500-merchant scale) to separate "archetype effect" from
"individual merchant effect."

**Volume**: false positives concentrate in low-volume merchant-days (279 vs
160 for higher-volume); false negatives concentrate in higher-volume ones
(48 vs 8). Consistent with the dataset validation finding that low-volume
merchants have noisier count-based rate features (more spurious signal →
more false alarms), while higher-volume merchants' genuine but
proportionally smaller deteriorations may be harder to separate from their
larger baseline (more real misses). Plausible, not proven.

## L. Recommended primary model

**Random Forest**, provisionally — it has the best PR-AUC at the
strongest horizon (0.603 at 30d, vs. 0.486 for logistic regression and
0.467 for XGBoost), the best false-positive profile of any model (132 FP
vs. 716 for the baseline, and the only model with FP:TP < 1 at 30d), a
non-degenerate, real median warning lead time (7 days, not an artifact),
and passes the shortcut audit with sensible, non-dominant feature
importances.

This is **not a clean win**: XGBoost and Logistic Regression are close on
F1 (0.553, 0.557 vs. RF's 0.526) at 30d, and Random Forest shows the
*largest* degradation under the temporal stress test of the three real
models (−21% relative PR-AUC). Logistic Regression is a genuinely
competitive, much simpler alternative at 30d (PR-AUC 0.486, F1 0.557,
better stress-test recall retention at 14d) and deserves serious
consideration as the simpler choice if interpretability or stress-test
stability is weighted more heavily than peak PR-AUC.

**Update (§E.1)**: probability calibration was implemented and evaluated
for this candidate and did **not** provide a clean improvement — Brier
score got slightly worse both on the normal test (0.188→0.192) and, more
so, under temporal stress (0.231→0.253), while discrimination metrics are
mathematically unchanged (sigmoid scaling is rank-preserving). Random
Forest / 30d remains the provisional candidate on **discrimination and
false-positive-profile grounds**, not on calibration grounds — its
probabilities (calibrated or not) should be treated as directionally
useful for ranking risk, not as literal, well-calibrated probabilities of
an elevated episode. Both the uncalibrated model and the calibrated
artifact are available (`data/metadata/modeling/artifacts/`); neither is
recommended as "calibrated and ready" — see §E.1 Limitations.

## M. Recommended primary horizon

**30 days.** It has the largest PR-AUC margin over chance for every model,
the only warning lead time with real, non-horizon-clamped runway (median 7
days for random_forest, out of a possible 30), and per D/§10, 7 days
leaves almost no separation from random. 30 days does not appear "too
broad" by the evidence gathered (precision at the chosen threshold is 0.50,
not degenerate; PR-AUC is well short of 1.0). This recommendation should be
revisited once precision/recall requirements from an actual product/ops
workflow are defined — this evaluation only shows which horizon the
*current* feature set and models can separate from noise, not which
horizon a merchant-facing product should use operationally.

## N. What remains uncertain

- **Archetype-level failure patterns** (K) are not statistically resolved
  at 8 test merchants — could be individual-merchant noise, not a real
  archetype effect.
- **Whether Random Forest's stress-test degradation is a property of the
  model class or of this specific feature set / training window** is
  untested — no other stress-test cutoffs were tried (only day_index=120),
  per the "don't tune endlessly" instruction.
- **Calibration was assessed but not corrected** — whether isotonic/Platt
  scaling would materially change the model comparison is unknown; it
  wasn't attempted in this pass.
- **The regression secondary problem is inconclusive** — a persistence
  baseline beating the RF candidate suggests either the 55-feature set
  lacks the right signal for *magnitude* prediction (vs. the binary
  elevation task it was designed around) or the regression target needs
  different treatment (e.g. quantile regression given the zero-inflated
  distribution) — not diagnosed further here, per the explicit instruction
  not to over-invest in this secondary problem.
- **The false-positive cost figures (F) are illustrative only** — no
  attempt was made to derive a "correct" cost, and none should be inferred
  from this report.
- **compound_risk's very high false-positive rate (K)** could reflect
  either over-triggering or early-correct detection ahead of the label;
  this benchmark's data cannot distinguish the two without deeper,
  slower case-by-case review not performed here.

## O. Is Sentinel ready to expose these outputs to the product layer?

**No.** This is a first baseline pass on a synthetic benchmark, evaluated
honestly, including a real bug found and fixed in the signature metric
during this same pass (G). Before anything here reaches a product surface:

- Calibration should be corrected (or explicitly surfaced as uncalibrated)
  if probabilities are shown to a user.
- The temporal stress-test degradation at 30d (H) needs to be understood,
  not just measured, before trusting the model under real drift.
- The archetype-level failure disparities (K) need re-evaluation at a
  larger merchant count before ruling out an archetype-driven shortcut.
- The false-positive cost assumption (F) is a placeholder for illustrating
  trade-offs — a real deployment needs an actual, stakeholder-reviewed cost
  model, not this synthetic one.
- This is entirely synthetic-benchmark evidence. It demonstrates the
  pipeline can produce a defensible, audited, non-leaking evaluation — it
  does **not** demonstrate real-world predictive validity, and Sentinel
  must not claim it does, nor claim any access to real Razorpay data or
  proprietary risk signals.

**What this stage does establish**: the feature/label/split pipeline is
leakage-audited and reproducible end to end, all three horizons and four
required models were evaluated on their actual merits (not assumed), a
genuinely wrong result was caught and corrected before being reported, and
there is a documented, evidence-based (if provisional) basis for
continuing to Random Forest / 30-day horizon as the next stage's starting
point — to be revisited, not treated as final.
