# SHAP Explainability Layer

Source: [`ml/explainability/`](../../ml/explainability/)
Regenerate with: [`scripts/run_explainability.py`](../../scripts/run_explainability.py)
Tests: [`tests/test_explainability.py`](../../tests/test_explainability.py)

## What this is

The layer between a verified model prediction and any future
product-facing explanation:

```
causal features → trained model → verified prediction → SHAP → structured explanation
```

This module computes SHAP (SHapley Additive exPlanations) attributions for
the provisional Random Forest / 30-day artifact and packages them into
deterministic, machine-readable objects. **It does not generate prose.**
The future product/LLM layer converts these verified objects into language
— it never invents the underlying numbers. Per `PROJECT_CONTEXT.md`: the
LLM is not the risk engine and must never independently calculate or
invent risk.

## Exact artifact explained

`data/metadata/modeling/artifacts/random_forest_calibrated_30d.joblib` +
its companion `..._config.json` — the same artifact produced by
`scripts/evaluate_calibration.py` (see `docs/research/baseline_ml_report.md`
§E.1). Loaded via `ml.explainability.artifact.load_artifact()`, which
**refuses to proceed** (raises, does not warn-and-continue) if: the file is
missing, it isn't a `CalibratedClassifierCV`, it doesn't unwrap to exactly
one `RandomForestClassifier`, its horizon doesn't match the expected 30
days, or its feature count doesn't match its own recorded column list.
Nothing here retrains, refits, or substitutes a different model.

### Two related probabilities — never conflated

The saved artifact is a `RandomForestClassifier` wrapped in a sigmoid
calibration layer (`ml/modeling/calibration.py`). Two numbers exist for
every row, and every explanation in this module reports both, labeled:

- **`model_probability_calibrated`** — `calibrated_pipeline.predict_proba(X)[:,1]`,
  the artifact's official output, compared against `decision_threshold`
  (0.6418) for the actual positive/negative call.
- **`model_probability_raw_rf`** — `base_random_forest.predict_proba(X)[:,1]`,
  the pre-calibration tree-ensemble score. **SHAP explains this one.**

**Why explain the raw score, not the calibrated one**: SHAP's TreeExplainer
computes *exact* Shapley values for tree ensembles — no sampling, no
approximation of the attribution itself. The sigmoid calibration layer on
top is a 2-parameter monotonic rescaling with no per-feature structure for
SHAP to decompose; treating the whole pipeline as a black box would force a
model-agnostic, sampling-based explainer (Kernel/Permutation SHAP),
trading exactness for generality we don't need here. Because the
calibration layer is monotonic, it cannot change which examples rank above
others or which features move a prediction up or down — the baseline ML
report already established this empirically (calibrated and uncalibrated
RF have identical precision/recall/F1/PR-AUC, which can only happen if
ranking is preserved exactly). So explaining the raw score gives the same
qualitative drivers and directions a user would see from the calibrated
number, while giving an *exact*, verifiable attribution — see Faithfulness
below.

## Why SHAP

Random Forest feature importances (`feature_importances_`, used in the
baseline report's shortcut audit) are global, impurity-based, and say
nothing about a *specific* merchant-day. SHAP provides:
- **Per-prediction attribution** — how much did each feature push *this*
  row's score up or down, not just "which features matter on average."
- **Signed, additive contributions** — attributions sum exactly to
  (prediction − baseline), so "why did the score come out this way" has a
  literal, checkable answer rather than a plausible-sounding one.
- **A method matched to the model** — TreeExplainer is exact for tree
  ensembles (see Faithfulness), unlike generic surrogate/perturbation
  methods.

## Local explanations

One structured object per (merchant_id, as_of_date) — see
`local_explanation.py`. Each contains: the calibrated and raw
probabilities, the decision threshold and call, the SHAP base value, the
reconstructed probability and reconstruction error (faithfulness), and
`top_positive_contributors` / `top_negative_contributors` (top 6 each,
`all_contributors` holds all 55). Each driver carries:

```
feature, group, definition, window, kind   (from the feature manifest — never re-derived from the name)
value                                       (this row's actual feature value)
shap_value                                  (signed contribution to the raw RF score)
direction                                   ("increases_risk" | "decreases_risk" | "neutral" — from the SHAP sign only)
```

This is deliberately the same shape as the task's example schema — a
future product layer turns a `top_positive_contributors` entry for
`chargeback_rate_acceleration` into "chargeback velocity is contributing
materially to elevated risk," but that sentence is not generated here, and
every noun and number in it traces back to a verified field above.

## Global explanation

`global_explanation.py` aggregates SHAP values across the **normal test
split** for the 30-day horizon — the same merchant-level, temporal-cutoff-
respecting held-out set used throughout the baseline evaluation (960 rows,
never train data). Reports:
- **Feature ranking** by mean `|SHAP value|` (magnitude of typical impact,
  regardless of direction).
- **Mean signed SHAP** per feature (average direction — see the important
  caveat below).
- **Group ranking** (the 9 feature-engineering groups, summed mean
  `|SHAP|`).

This run's top group is `chargeback_behavior` (summed mean |SHAP| 0.254,
next is `temporal_velocity` at 0.058) and its top individual feature is
`chargeback_rate_28d` (mean |SHAP| 0.079) — consistent with, and a useful
cross-check against, the baseline report's independent (impurity-based)
finding that `chargeback_rate_28d` was the top `feature_importances_`
feature for this same Random Forest. Two different importance measures
agreeing is a mild positive signal, not a mathematical guarantee they must
agree — full ranking in `data/metadata/explainability/global_feature_importance.json`.

**Global importance is diagnostic only.** Nothing here selects, drops, or
reweights features, and no test in this module allows it to
(`test_global_importance_does_not_alter_feature_set`).

## Faithfulness (verified, not assumed)

For every row explained: `shap_base_value + sum(shap_values) == raw_probability`,
checked to a `1e-4` absolute tolerance (`config.FAITHFULNESS_ABS_TOLERANCE`).
In practice, on the full 960-row test set, the maximum observed
reconstruction error is **~3×10⁻¹⁵** — machine-precision floating point
noise, not approximation error. This is expected and documented, not
incidental: TreeSHAP is an *exact* algorithm for tree ensembles (Lundberg
et al., 2018), so a real deviation here would indicate a bug (e.g. a
class-index mix-up), not normal approximation slack. `run_explainability.py`
treats a faithfulness failure as fatal — it raises rather than publishing
explanations that don't reconstruct the model's own output.

**One documented approximation exists, upstream of SHAP**: `expected_value`
(the SHAP "base rate") reflects the *training-time-weighted* class balance
baked into the trees by `class_weight='balanced_subsample'` — empirically
≈0.5 for both classes — not the raw empirical positive rate of the test
set (~25%). This is a real, checked property of the underlying model (the
trees were fit on reweighted bootstrap samples), not a SHAP artifact, and
is why a raw "0.5 base + contributions" reads differently from "25% prior
+ contributions." Documented here rather than silently reconciled.

## Sign / direction — a genuine finding, not a hypothetical caveat

The task brief warns not to assume a feature is "risky" from its name.
Running this pipeline on real data produced a concrete illustration of
exactly why that warning matters: in **both** of the two highest-confidence
positive predictions inspected (`example_local_explanations.json`), the
chargeback-rate features (`chargeback_rate_7d/28d/60d`, `chargeback_count_28d`)
had a **value of exactly 0.0** — no chargebacks in the trailing windows —
and `days_since_last_chargeback` was high (41 and 90, near or at its cap)
— yet **all of these pushed the score higher** (`shap_value > 0`), not
lower. A "quiet" chargeback history is not, for these specific rows,
association with low risk in what the model learned. Global
`mean_signed_shap` for `chargeback_rate_28d` is slightly *negative*
(−0.013) — the opposite sign from what these two individual rows show —
which is not a contradiction: it demonstrates real interaction effects
(the Random Forest's learned relationship depends on combinations of
features, not one feature in isolation), and is precisely why **per-row
SHAP output, not a feature's name or its average direction, must be the
only source for any "X is contributing to elevated risk" statement.**
This is flagged as needing human investigation before product integration
(see Limitations) — it may reflect a genuine, if counter-intuitive, model
behavior, or it may reflect the low-transaction-volume/sparse-count
dynamics already documented as a benchmark limitation in
`docs/research/dataset_validation_report.md`. SHAP cannot distinguish
those two explanations; it only reports what the model actually did.

## Local vs. global — when to use which

- **Local** answers "why did the model score *this* merchant-day the way
  it did" — the unit a product surface or dispute-prep workflow needs.
- **Global** answers "what does this model lean on overall" — useful for
  model review, the shortcut audit, and sanity-checking that no single
  feature or feature group silently dominates (cross-referenced against
  `ml/modeling/shortcut_audit.py`'s dominance check from the baseline
  evaluation).
- Neither should be used interchangeably: a feature can be globally
  important and irrelevant to a specific prediction, or globally minor and
  decisive for one merchant-day (as above).

## Causal / leakage safety

Structural guarantees (tested in `tests/test_explainability.py`, not just
asserted):
- `leakage.assert_no_forbidden_columns()` rejects any feature name
  containing `baseline_`, `event_type`, `severity_score`,
  `label_elevated`, `archetype`, etc., or the exact names `merchant_id`,
  `day_index`, `date`, `as_of_date`, `business_tier`.
- `leakage.assert_columns_match_artifact()` requires the feature matrix's
  columns to match the artifact's own recorded `feature_columns_in_order`
  **exactly**, including order — not just "same set."
- Data loading reuses `ml.modeling.datasets` — the identical code path the
  baseline evaluation uses, which reads only `features.csv`/`labels.csv`/
  `merchants.csv` and never `events.csv` for anything feature-shaped.
- `run_explainability.py` calls both guards before computing anything,
  and fails loudly (raises) rather than silently proceeding if either
  check fails.

## What this does NOT establish

- **Not causal.** SHAP attributes the *model's* output to its inputs. It
  says "this is what the Random Forest did with these numbers," never
  "this feature caused this risk." The model itself was trained on
  synthetic, generator-produced data — an association the model learned
  is, at most, evidence about the benchmark's generative structure, not
  about real merchant behavior.
- **Not a real-world validity claim.** Every number in this pipeline
  traces back to the synthetic 50×180 benchmark. Nothing here has been
  checked against real transactions, and none of it should be presented as
  if it had.
- **Not a substitute for the false-positive/calibration caveats already on
  record.** The baseline and calibration reports' limitations (weak 7-day
  signal, temporal stress-test degradation, unresolved archetype-level
  disparities, calibration not clearly improving Brier score) all still
  apply to the model these explanations describe — SHAP explains the
  model faithfully; it does not make the model better or more validated.

## Limitations

- **Small test sample (960 rows) for global aggregation** — the same
  small-benchmark caveat that runs through every prior report in this
  project; mean |SHAP| rankings should be read directionally.
- **Explains one model only** (Random Forest / 30d) — Logistic Regression
  and XGBoost were not explained here (out of scope for this pass;
  Logistic Regression's coefficients are already inherently interpretable,
  and XGBoost would need its own TreeExplainer pass if it were ever
  selected instead).
- **The zero-value-pushes-risk-up finding above is flagged, not resolved**
  — a genuine open question for whoever integrates this into the product
  layer, not something this pass had scope to root-cause (would require
  partial-dependence or interaction-value analysis beyond this task's
  brief).
- **SHAP values are computed against the raw (uncalibrated) score**; a
  consumer that needs attributions in calibrated-probability units would
  need a different (approximate) approach — not implemented here, and not
  needed for the qualitative "what's driving this" use case this layer
  serves.
