"""
Orchestrates the full baseline ML evaluation: for each horizon, fit every
model on the merchant-level train split, select a decision threshold on
validation, then evaluate on the normal held-out test AND the temporal
stress test. Returns a JSON-serializable results dict plus in-memory
structures (plot data, per-row predictions) used by scripts/run_baseline_ml.py
for plotting and failure analysis.

This module does not decide anything about "the winner" — that judgment
call, and the narrative around it, belongs in the report
(docs/research/baseline_ml_report.md) and the CLI script's summary, not
buried in orchestration code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import datasets, metrics, models as models_module, shortcut_audit, warning_lead_time
from .config import BASELINE_SIGNAL_FEATURE, HORIZONS, SEED


@dataclass
class EvaluationOutputs:
    results: dict
    pr_plot_data: dict = field(default_factory=dict)
    calibration_plot_data: dict = field(default_factory=dict)
    lead_time_plot_data: dict = field(default_factory=dict)
    comparison_rows: list = field(default_factory=list)
    predictions_store: dict = field(default_factory=dict)  # {horizon: {model: {"frame":..., "y_true":..., "y_pred":..., "scores":...}}}
    frames_store: dict = field(default_factory=dict)  # {horizon: {"train":..., "val":..., "normal_test":..., "stress_test":...}}


def _strip_for_json(d: dict) -> dict:
    """Drop the (large, non-essential-for-JSON) per-episode list from the
    warning-lead-time block to keep results.json readable; the full episode
    list is still available in-memory via EvaluationOutputs for anyone who
    wants it during this run.
    """
    out = dict(d)
    if "warning_lead_time" in out:
        wlt = dict(out["warning_lead_time"])
        wlt.pop("episodes", None)
        out["warning_lead_time"] = wlt
    return out


def run_full_evaluation(tables: dict, feature_cols: list[str], split_df: pd.DataFrame) -> EvaluationOutputs:
    out = EvaluationOutputs(results={"seed": SEED, "horizons_evaluated": HORIZONS, "by_horizon": {}})

    for h in HORIZONS:
        frame = datasets.build_horizon_frame(tables, h)
        frame = datasets.apply_merchant_split(frame, split_df)
        frames = datasets.train_val_test_frames(frame)
        out.frames_store[h] = frames

        X_train, y_train = datasets.xy(frames["train"], feature_cols)
        X_val, y_val = datasets.xy(frames["val"], feature_cols)
        X_test, y_test = datasets.xy(frames["normal_test"], feature_cols)
        has_stress = len(frames["stress_test"]) > 0
        if has_stress:
            X_stress, y_stress = datasets.xy(frames["stress_test"], feature_cols)

        model_instances = models_module.build_models(feature_cols, BASELINE_SIGNAL_FEATURE)
        horizon_result = {
            "n_train": int(len(y_train)),
            "n_val": int(len(y_val)),
            "n_test": int(len(y_test)),
            "n_stress_test": int(len(y_stress)) if has_stress else 0,
            "positive_rate_train": float(y_train.mean()),
            "positive_rate_val": float(y_val.mean()),
            "positive_rate_test": float(y_test.mean()),
            "positive_rate_stress_test": float(y_stress.mean()) if has_stress else None,
            "models": {},
        }

        importances_by_model = {}
        out.predictions_store[h] = {}

        for name, model in model_instances.items():
            model.fit(X_train, y_train)

            score_val = model.predict_score(X_val)
            threshold = metrics.select_threshold_maximizing_f1(y_val, score_val)

            score_test = model.predict_score(X_test)
            test_cls = metrics.classification_metrics(y_test, score_test, threshold)

            prob_test = score_test if getattr(model, "is_probabilistic", True) else model.predict_pseudo_probability(X_test)
            calib = metrics.calibration_assessment(y_test, prob_test)
            fp_cost = metrics.false_positive_cost_analysis(test_cls["confusion_matrix"])

            y_pred_test = (score_test >= threshold).astype(int)
            wlt = warning_lead_time.compute_warning_lead_times(frames["normal_test"], y_pred_test, h)

            stress_cls = None
            if has_stress:
                score_stress = model.predict_score(X_stress)
                stress_cls = metrics.classification_metrics(y_stress, score_stress, threshold)

            model_entry = {
                "threshold_selected_on_val": threshold,
                "test": test_cls,
                "stress_test": stress_cls,
                "calibration": calib,
                "false_positive_cost": fp_cost,
                "warning_lead_time": wlt,
            }
            horizon_result["models"][name] = _strip_for_json(model_entry)

            if hasattr(model, "feature_importances"):
                importances_by_model[name] = model.feature_importances(feature_cols)

            out.pr_plot_data.setdefault(h, {})[name] = (y_test, score_test, float(y_test.mean()))
            out.calibration_plot_data.setdefault(h, {})[name] = calib["reliability_curve"]
            out.lead_time_plot_data.setdefault(h, {})[name] = [e["lead_time_days"] for e in wlt["episodes"] if e["status"] == "early"]

            out.predictions_store[h][name] = {
                "frame": frames["normal_test"],
                "y_true": y_test,
                "y_pred": y_pred_test,
                "scores": score_test,
            }

            out.comparison_rows.append(
                {
                    "model": name,
                    "horizon": h,
                    "precision": test_cls["precision"],
                    "recall": test_cls["recall"],
                    "f1": test_cls["f1"],
                    "pr_auc": test_cls["pr_auc"],
                    "roc_auc_secondary": test_cls["roc_auc_secondary"],
                    "brier_score": calib["brier_score"],
                    "calibration_verdict": calib["verdict"],
                    "false_positives_per_true_positive": fp_cost["false_positives_per_true_positive"],
                    "median_warning_lead_time_days": wlt["median_warning_lead_time_days"],
                    "n_episodes_total": wlt["n_episodes_total"],
                    "n_early_warning": wlt["n_early_warning"],
                    "stress_pr_auc": stress_cls["pr_auc"] if stress_cls else None,
                    "stress_recall": stress_cls["recall"] if stress_cls else None,
                }
            )

        audit = shortcut_audit.run_full_audit(X_train, y_train, feature_cols, importances_by_model)
        horizon_result["shortcut_audit"] = audit
        horizon_result["feature_importances"] = importances_by_model

        out.results["by_horizon"][h] = horizon_result

    out.results["overall_shortcut_audit_pass"] = all(
        out.results["by_horizon"][h]["shortcut_audit"]["overall_pass"] for h in HORIZONS
    )
    return out
