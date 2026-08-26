#!/usr/bin/env python3
"""
Build SHAP explanations for Sentinel's provisional Random Forest / 30-day
artifact: global feature importance over the held-out test set, plus a
handful of illustrative individual explanations.

Reads ONLY the already-validated causal feature matrix (via
ml.modeling.datasets, the same code path as the baseline evaluation) and
the saved model artifact. Never touches the generator, feature
definitions, labels-as-features, or event/scenario metadata as inputs.

Usage:
    python scripts/run_explainability.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from ml.explainability import artifact as artifact_module
from ml.explainability import global_explanation, io_utils, leakage, local_explanation, plots, shap_engine
from ml.explainability.config import OUTPUT_DIR, PLOTS_DIR
from ml.explainability.feature_metadata import load_feature_metadata
from ml.modeling import datasets, splits
from ml.modeling.config import SEED


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model artifact ...")
    loaded = artifact_module.load_artifact()
    print(f"  artifact: {loaded.artifact_path}")
    print(f"  horizon_days: {loaded.horizon_days}, decision_threshold: {loaded.decision_threshold:.4f}")
    print(f"  n_features: {len(loaded.feature_columns)}")

    print("Verifying feature set has no forbidden columns ...")
    leakage.assert_no_forbidden_columns(loaded.feature_columns)

    print("Loading causal feature/label data (same split as baseline evaluation) ...")
    tables = datasets.load_raw_tables()
    feature_cols = datasets.load_feature_columns()
    leakage.assert_columns_match_artifact(feature_cols, loaded.feature_columns)

    split_df = splits.build_merchant_split(tables["merchants"], seed=SEED)
    frame = datasets.build_horizon_frame(tables, loaded.horizon_days)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)
    test_frame = frames["normal_test"]

    X_test, y_test = datasets.xy(test_frame, loaded.feature_columns)
    print(f"  n_test rows: {len(y_test)}")

    print("Building SHAP TreeExplainer and computing SHAP values over the test set ...")
    explainer = shap_engine.build_explainer(loaded.base_random_forest)
    shap_result = shap_engine.compute_shap_values(explainer, loaded.base_random_forest, X_test)
    print(f"  max |reconstruction error| = {shap_result.max_abs_reconstruction_error:.2e}  faithful={shap_result.faithful}")
    if not shap_result.faithful:
        raise RuntimeError("SHAP faithfulness check failed — refusing to publish explanations. Investigate before proceeding.")

    print("Computing global feature importance ...")
    metadata_by_name = load_feature_metadata()
    global_result = global_explanation.global_feature_importance(shap_result, loaded.feature_columns, metadata_by_name)
    io_utils.write_json(
        {
            "artifact_path": str(loaded.artifact_path),
            "horizon_days": loaded.horizon_days,
            "evaluation_sample": "merchant-level normal test split (held out, temporal early period)",
            **global_result,
        },
        OUTPUT_DIR / "global_feature_importance.json",
    )
    plots.plot_global_importance(global_result, PLOTS_DIR / "global_feature_importance.png")
    print("  top 5 features by mean |SHAP|:")
    for entry in global_result["feature_ranking"][:5]:
        print(f"    {entry['rank']}. {entry['feature']} ({entry['group']}): {entry['mean_abs_shap']:.4f}")

    print("Selecting illustrative examples for local explanations ...")
    calibrated_probability = loaded.calibrated_pipeline.predict_proba(X_test)[:, 1]
    predicted_positive = calibrated_probability >= loaded.decision_threshold

    idx_true_positive = None
    positive_mask = y_test == 1
    if positive_mask.any():
        idx_true_positive = int(np.argmax(np.where(positive_mask, calibrated_probability, -1)))

    idx_false_positive = None
    fp_mask = (y_test == 0) & predicted_positive
    if fp_mask.any():
        idx_false_positive = int(np.argmax(np.where(fp_mask, calibrated_probability, -1)))

    idx_borderline = int(np.argmin(np.abs(calibrated_probability - loaded.decision_threshold)))

    selected = {
        "highest_confidence_true_positive": idx_true_positive,
        "highest_confidence_false_positive": idx_false_positive,
        "borderline_case": idx_borderline,
    }
    selected = {k: v for k, v in selected.items() if v is not None}

    explanations = {}
    for label, idx in selected.items():
        exp = local_explanation.explain_row(
            row_index=idx,
            X_row=X_test[idx],
            shap_result=shap_result,
            feature_columns=loaded.feature_columns,
            metadata_by_name=metadata_by_name,
            artifact=loaded,
            calibrated_probability=calibrated_probability[idx],
            merchant_id=str(test_frame.iloc[idx]["merchant_id"]),
            as_of_date=str(test_frame.iloc[idx]["as_of_date"].date()),
            day_index=int(test_frame.iloc[idx]["day_index"]),
        )
        explanations[label] = exp.to_dict()
        print(f"  {label}: {exp.merchant_id} @ {exp.as_of_date}  p_calibrated={exp.model_probability_calibrated:.3f}  faithful={exp.faithful}")

    io_utils.write_json(
        {
            "artifact_path": str(loaded.artifact_path),
            "horizon_days": loaded.horizon_days,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "examples": explanations,
        },
        OUTPUT_DIR / "example_local_explanations.json",
    )

    if "highest_confidence_true_positive" in explanations:
        plots.plot_local_drivers(explanations["highest_confidence_true_positive"], PLOTS_DIR / "local_explanation_example.png")

    print(f"\nWrote {OUTPUT_DIR / 'global_feature_importance.json'}")
    print(f"Wrote {OUTPUT_DIR / 'example_local_explanations.json'}")
    print(f"Wrote plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
