#!/usr/bin/env python3
"""
Evaluate and implement probability calibration for the provisional
Random Forest / 30-day candidate from docs/research/baseline_ml_report.md.

Reuses the EXACT same merchant-level split, temporal-cutoff methodology,
and feature set as the baseline evaluation (ml/modeling/splits.py,
datasets.py, config.py) — nothing about the split or features changes here.

Does NOT touch the synthetic generator or feature-engineering pipeline.

Writes:
    data/metadata/modeling/calibration_results.json
    data/metadata/modeling/calibration_comparison_table.csv
    data/metadata/modeling/artifacts/random_forest_calibrated_30d.joblib
    data/metadata/modeling/artifacts/random_forest_calibrated_30d_config.json
    data/metadata/modeling/plots/calibration_before_after.png

Usage:
    python scripts/evaluate_calibration.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import joblib
import numpy as np
import sklearn

from ml.modeling import datasets, metrics, splits, warning_lead_time
from ml.modeling.calibration import CALIBRATION_METHOD, VAL_CALIBRATION_FRACTION, CalibratedRandomForestModel, split_validation_for_calibration
from ml.modeling.config import (
    FEATURES_PATH,
    LABELS_PATH,
    MERCHANTS_PATH,
    OUTPUT_DIR,
    PLOTS_DIR,
    RANDOM_FOREST_PARAMS,
    SEED,
    TEMPORAL_CUTOFF_DAY_INDEX,
)
from ml.modeling.models import RandomForestModel

HORIZON = 30
ARTIFACT_DIR = OUTPUT_DIR / "artifacts"


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def evaluate_variant(name, frame_normal_test, y_test, score_test, frame_stress, y_stress, score_stress, threshold, horizon):
    test_cls = metrics.classification_metrics(y_test, score_test, threshold)
    calib = metrics.calibration_assessment(y_test, score_test)
    fp_cost = metrics.false_positive_cost_analysis(test_cls["confusion_matrix"])
    y_pred_test = (score_test >= threshold).astype(int)
    wlt = warning_lead_time.compute_warning_lead_times(frame_normal_test, y_pred_test, horizon)

    stress_cls = metrics.classification_metrics(y_stress, score_stress, threshold) if len(y_stress) else None
    stress_calib = metrics.calibration_assessment(y_stress, score_stress) if len(y_stress) else None

    wlt_summary = {k: v for k, v in wlt.items() if k != "episodes"}
    return {
        "name": name,
        "threshold": threshold,
        "test": test_cls,
        "calibration": calib,
        "false_positive_cost": fp_cost,
        "warning_lead_time": wlt_summary,
        "stress_test": stress_cls,
        "stress_calibration": stress_calib,
    }, calib["reliability_curve"]


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Evaluating calibration for random_forest at the {HORIZON}-day horizon ...")
    tables = datasets.load_raw_tables()
    feature_cols = datasets.load_feature_columns()

    split_df = splits.build_merchant_split(tables["merchants"], seed=SEED)
    frame = datasets.build_horizon_frame(tables, HORIZON)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)

    X_train, y_train = datasets.xy(frames["train"], feature_cols)
    X_val, y_val = datasets.xy(frames["val"], feature_cols)
    X_test, y_test = datasets.xy(frames["normal_test"], feature_cols)
    X_stress, y_stress = datasets.xy(frames["stress_test"], feature_cols)

    print(f"  n_train={len(y_train)}  n_val={len(y_val)}  n_test={len(y_test)}  n_stress={len(y_stress)}")

    val_split = split_validation_for_calibration(X_val, y_val)
    print(f"  val split for calibration: n_val_calibration={len(val_split.y_calibration)}  n_val_threshold={len(val_split.y_threshold)}")

    # --- Uncalibrated Random Forest (identical hyperparameters to baseline;
    # threshold re-selected on val_threshold for a like-for-like comparison
    # with the calibrated variant — see docs/research/baseline_ml_report.md) ---
    print("Fitting uncalibrated Random Forest (train only) ...")
    uncalibrated = RandomForestModel()
    uncalibrated.fit(X_train, y_train)
    uncal_score_val_threshold = uncalibrated.predict_score(val_split.X_threshold)
    uncal_threshold = metrics.select_threshold_maximizing_f1(val_split.y_threshold, uncal_score_val_threshold)

    uncal_score_test = uncalibrated.predict_score(X_test)
    uncal_score_stress = uncalibrated.predict_score(X_stress)

    uncal_result, uncal_curve = evaluate_variant(
        "random_forest_uncalibrated", frames["normal_test"], y_test, uncal_score_test,
        frames["stress_test"], y_stress, uncal_score_stress, uncal_threshold, HORIZON,
    )

    # --- Calibrated Random Forest ---
    print(f"Fitting calibrated Random Forest ({CALIBRATION_METHOD} scaling, fit on train + val_calibration only) ...")
    calibrated = CalibratedRandomForestModel()
    calibrated.fit_calibrated(X_train, y_train, val_split.X_calibration, val_split.y_calibration)

    cal_score_val_threshold = calibrated.predict_score(val_split.X_threshold)
    cal_threshold = metrics.select_threshold_maximizing_f1(val_split.y_threshold, cal_score_val_threshold)

    cal_score_test = calibrated.predict_score(X_test)
    cal_score_stress = calibrated.predict_score(X_stress)

    cal_result, cal_curve = evaluate_variant(
        "random_forest_calibrated", frames["normal_test"], y_test, cal_score_test,
        frames["stress_test"], y_stress, cal_score_stress, cal_threshold, HORIZON,
    )

    # --- Leakage self-checks (structural, see tests/test_calibration.py for
    # the automated/regression version of these) ---
    importances_before = uncalibrated.feature_importances(feature_cols)
    importances_after = calibrated.feature_importances(feature_cols)
    base_model_unchanged_by_calibration = importances_before == importances_after or all(
        abs(importances_before[k] - importances_after[k]) < 1e-12 for k in importances_before
    )
    # NOTE: uncalibrated and calibrated use SEPARATE RandomForestClassifier
    # instances (both fit on identical X_train/y_train with the same seeded
    # hyperparameters), so this checks determinism, not literal object
    # identity — see tests/test_calibration.py for the identity-based check
    # against calibrated.base_model directly.

    leakage_checks = {
        "test_set_never_passed_to_any_fit_call": True,  # structural: fit_calibrated()'s signature has no X_test parameter
        "calibration_fit_only_on_val_calibration_slice": True,  # structural: CalibratedClassifierCV(cv='prefit').fit(X_val_calibration, ...)
        "base_random_forest_feature_importances_deterministic_given_same_train_data": base_model_unchanged_by_calibration,
        "val_calibration_and_val_threshold_are_disjoint": len(set(map(tuple, val_split.X_calibration.tolist())) & set(map(tuple, val_split.X_threshold.tolist()))) == 0,
    }

    # --- Save results ---
    comparison_rows = [
        {
            "variant": r["name"],
            "threshold": r["threshold"],
            "precision": r["test"]["precision"],
            "recall": r["test"]["recall"],
            "f1": r["test"]["f1"],
            "pr_auc": r["test"]["pr_auc"],
            "brier_score": r["calibration"]["brier_score"],
            "calibration_verdict": r["calibration"]["verdict"],
            "false_positives_per_true_positive": r["false_positive_cost"]["false_positives_per_true_positive"],
            "median_warning_lead_time_days": r["warning_lead_time"]["median_warning_lead_time_days"],
            "stress_pr_auc": r["stress_test"]["pr_auc"] if r["stress_test"] else None,
            "stress_precision": r["stress_test"]["precision"] if r["stress_test"] else None,
            "stress_recall": r["stress_test"]["recall"] if r["stress_test"] else None,
            "stress_brier_score": r["stress_calibration"]["brier_score"] if r["stress_calibration"] else None,
        }
        for r in [uncal_result, cal_result]
    ]

    full_results = {
        "run_metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "horizon": HORIZON,
            "seed": SEED,
            "temporal_cutoff_day_index": TEMPORAL_CUTOFF_DAY_INDEX,
            "calibration_method": CALIBRATION_METHOD,
            "val_calibration_fraction": VAL_CALIBRATION_FRACTION,
            "input_file_hashes_sha256_16": {
                "features.csv": _sha256(FEATURES_PATH),
                "labels.csv": _sha256(LABELS_PATH),
                "merchants.csv": _sha256(MERCHANTS_PATH),
            },
            "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__, "joblib": joblib.__version__},
        },
        "sample_sizes": {
            "n_train": len(y_train), "n_val": len(y_val),
            "n_val_calibration": len(val_split.y_calibration), "n_val_threshold": len(val_split.y_threshold),
            "n_test": len(y_test), "n_stress_test": len(y_stress),
        },
        "uncalibrated": uncal_result,
        "calibrated": cal_result,
        "leakage_checks": leakage_checks,
        "comparison_table": comparison_rows,
    }
    (OUTPUT_DIR / "calibration_results.json").write_text(json.dumps(full_results, indent=2, default=_json_default))

    import pandas as pd

    pd.DataFrame(comparison_rows).to_csv(OUTPUT_DIR / "calibration_comparison_table.csv", index=False)

    # --- Plot: before/after reliability curves ---
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, label="perfectly calibrated")
    ax.plot(uncal_curve["mean_predicted"], uncal_curve["observed_frequency"], marker="o", label="uncalibrated RF", color="#c0392b")
    ax.plot(cal_curve["mean_predicted"], cal_curve["observed_frequency"], marker="o", label="calibrated RF (sigmoid)", color="#2471a3")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Calibration before/after — Random Forest, {HORIZON}-day horizon (test set)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "calibration_before_after.png", dpi=130)
    plt.close(fig)

    # --- Save the artifact ---
    artifact_path = ARTIFACT_DIR / "random_forest_calibrated_30d.joblib"
    joblib.dump(calibrated.calibrator, artifact_path)

    config_path = ARTIFACT_DIR / "random_forest_calibrated_30d_config.json"
    config_path.write_text(
        json.dumps(
            {
                "artifact_file": artifact_path.name,
                "artifact_type": "sklearn.calibration.CalibratedClassifierCV (method='prefit', wraps a RandomForestClassifier)",
                "horizon_days": HORIZON,
                "decision_threshold": cal_threshold,
                "feature_columns_in_order": feature_cols,
                "calibration_method": CALIBRATION_METHOD,
                "random_forest_params": {**RANDOM_FOREST_PARAMS, "n_jobs": 1},  # n_jobs pinned to 1 for this artifact for deterministic inference — see calibration.py / report §E.1 Limitations
                "seed": SEED,
                "temporal_cutoff_day_index": TEMPORAL_CUTOFF_DAY_INDEX,
                "trained_on": "merchant-level train split (n={})".format(len(y_train)),
                "calibrated_on": "merchant-level val split, calibration half (n={}, disjoint from val_threshold)".format(len(val_split.y_calibration)),
                "input_file_hashes_sha256_16": full_results["run_metadata"]["input_file_hashes_sha256_16"],
                "environment": full_results["run_metadata"]["environment"],
                "usage": "predict_proba(X)[:, 1] on a DataFrame/array with columns in EXACTLY feature_columns_in_order; predict positive if score >= decision_threshold.",
                "timestamp_utc": full_results["run_metadata"]["timestamp_utc"],
            },
            indent=2,
        )
    )

    print("\n=== Comparison (test set) ===")
    print(pd.DataFrame(comparison_rows)[["variant", "precision", "recall", "f1", "pr_auc", "brier_score", "median_warning_lead_time_days"]].to_string(index=False))
    print(f"\nLeakage checks: {leakage_checks}")
    print(f"\nWrote {OUTPUT_DIR / 'calibration_results.json'}")
    print(f"Wrote {artifact_path}")
    print(f"Wrote {config_path}")
    print(f"Wrote {PLOTS_DIR / 'calibration_before_after.png'}")


if __name__ == "__main__":
    main()
