#!/usr/bin/env python3
"""
Run the full Sentinel baseline ML evaluation: classification (7/14/30-day
horizons x 4 models), the secondary chargeback-exposure regression, the
feature/shortcut audit, and failure analysis.

Reads ONLY the already-built, already-validated artifacts:
    data/processed/features.csv
    data/processed/labels.csv
    data/raw/merchants.csv
    data/scenarios/events.csv   (failure analysis only, never a feature)

Never modifies the generator or the feature-engineering pipeline. See
docs/research/baseline_ml_report.md for the full write-up.

Usage:
    python scripts/run_baseline_ml.py
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

import numpy as np
import pandas as pd
import sklearn

from ml.modeling import datasets, failure_analysis, plots, regression, splits
from ml.modeling.config import (
    EVENTS_PATH,
    FEATURES_PATH,
    HORIZONS,
    LABELS_PATH,
    MERCHANTS_PATH,
    OUTPUT_DIR,
    PLOTS_DIR,
    SEED,
    TEMPORAL_CUTOFF_DAY_INDEX,
)
from ml.modeling.evaluate import run_full_evaluation
from ml.modeling.models import XGBOOST_AVAILABLE, XGBOOST_IMPORT_ERROR


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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"XGBoost available: {XGBOOST_AVAILABLE}" + ("" if XGBOOST_AVAILABLE else f" ({XGBOOST_IMPORT_ERROR})"))

    print("Loading inputs ...")
    tables = datasets.load_raw_tables()
    feature_cols = datasets.load_feature_columns()
    events = pd.read_csv(EVENTS_PATH, parse_dates=["start_date", "end_date", "recovery_end_date"])

    print("Building merchant-level, archetype-stratified split ...")
    split_df = splits.build_merchant_split(tables["merchants"], seed=SEED)
    split_info = splits.split_summary(split_df)
    for split_name in ["train", "val", "test"]:
        print(f"  {split_name}: {split_info['overall_counts'].get(split_name, 0)} merchants ({split_info['overall_fractions'].get(split_name, 0):.1%})")

    print("Running classification evaluation for all horizons x models ...")
    outputs = run_full_evaluation(tables, feature_cols, split_df)

    print("Running secondary regression evaluation (future_chargeback_amount) ...")
    regression_results = {}
    for h in HORIZONS:
        frames = outputs.frames_store[h]
        X_train, y_train_reg = datasets.xy(frames["train"], feature_cols, target_col="future_chargeback_amount")
        X_test, y_test_reg = datasets.xy(frames["normal_test"], feature_cols, target_col="future_chargeback_amount")

        naive_pred = regression.naive_baseline(frames["normal_test"], h)
        naive_metrics = regression.regression_metrics(y_test_reg, naive_pred)

        rf_model = regression.fit_regression_candidate(X_train, y_train_reg)
        rf_pred = regression.predict_regression_candidate(rf_model, X_test)
        rf_metrics = regression.regression_metrics(y_test_reg, rf_pred)

        regression_results[h] = {"naive_trailing_baseline": naive_metrics, "random_forest_candidate": rf_metrics}
        print(f"  h={h}d  naive MAE={naive_metrics['mae']:.1f}  RF MAE={rf_metrics['mae']:.1f}")

    print("Running failure analysis (all model x horizon combinations) ...")
    failure_results = {}
    for h in HORIZONS:
        failure_results[h] = {}
        for name, pred_data in outputs.predictions_store[h].items():
            failure_results[h][name] = failure_analysis.analyze_errors(
                pred_data["frame"], pred_data["y_true"], pred_data["y_pred"], events
            )

    print("Generating plots ...")
    plots.plot_pr_curves_by_horizon(outputs.pr_plot_data, PLOTS_DIR / "pr_curves_by_horizon.png")
    plots.plot_calibration_by_horizon(outputs.calibration_plot_data, PLOTS_DIR / "calibration_by_horizon.png")
    plots.plot_warning_lead_time_distribution(outputs.lead_time_plot_data, PLOTS_DIR / "warning_lead_time_distribution.png")
    plots.plot_model_horizon_comparison(outputs.comparison_rows, "pr_auc", "PR-AUC", PLOTS_DIR / "comparison_pr_auc.png")
    plots.plot_model_horizon_comparison(outputs.comparison_rows, "f1", "F1", PLOTS_DIR / "comparison_f1.png")

    # One representative error-breakdown plot: random_forest at the middle
    # horizon (14d) — avoids generating 12 near-identical plots.
    rep_model, rep_horizon = "random_forest", 14
    if rep_horizon in failure_results and rep_model in failure_results[rep_horizon]:
        fa = failure_results[rep_horizon][rep_model]
        plots.plot_error_breakdown(
            fa["false_positive_breakdown"]["by_active_event_type"],
            fa["false_negative_breakdown"]["by_active_event_type"],
            f"Error breakdown by active scenario type — {rep_model}, {rep_horizon}d horizon",
            PLOTS_DIR / "error_breakdown_by_scenario.png",
        )

    print("Writing results ...")
    comparison_df = pd.DataFrame(outputs.comparison_rows)
    comparison_df.to_csv(OUTPUT_DIR / "comparison_table.csv", index=False)

    full_results = {
        "run_metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "temporal_cutoff_day_index": TEMPORAL_CUTOFF_DAY_INDEX,
            "input_file_hashes_sha256_16": {
                "features.csv": _sha256(FEATURES_PATH),
                "labels.csv": _sha256(LABELS_PATH),
                "merchants.csv": _sha256(MERCHANTS_PATH),
            },
            "environment": {
                "python": platform.python_version(),
                "sklearn": sklearn.__version__,
                "xgboost_available": XGBOOST_AVAILABLE,
                "xgboost_import_error": XGBOOST_IMPORT_ERROR,
            },
        },
        "split": split_info,
        "classification": outputs.results,
        "regression_secondary_problem": regression_results,
        "failure_analysis": failure_results,
        "comparison_table": outputs.comparison_rows,
    }
    (OUTPUT_DIR / "results.json").write_text(json.dumps(full_results, indent=2, default=_json_default))

    print("\n=== Comparison table (test set) ===")
    print(comparison_df[["model", "horizon", "precision", "recall", "f1", "pr_auc", "median_warning_lead_time_days"]].to_string(index=False))
    print(f"\nOverall shortcut audit pass: {outputs.results['overall_shortcut_audit_pass']}")
    print(f"Wrote {OUTPUT_DIR / 'results.json'}")
    print(f"Wrote {OUTPUT_DIR / 'comparison_table.csv'}")
    print(f"Wrote plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
