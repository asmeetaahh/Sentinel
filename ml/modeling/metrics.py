"""
Classification metrics, calibration diagnostics, and false-positive cost
accounting. PR-AUC is treated as the primary ranking metric (per
PROJECT_CONTEXT.md — this is a risk-event-detection task, not a balanced
classification task); ROC-AUC is computed only as a secondary diagnostic.
"""

from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .config import ASSUMED_COST_PER_FALSE_POSITIVE, BENEFIT_PER_TRUE_POSITIVE_SENSITIVITY


def select_threshold_maximizing_f1(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Chosen on VALIDATION data only; applied fixed to test/stress sets."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, scores)
    f1s = np.where((precisions + recalls) > 0, 2 * precisions * recalls / np.maximum(precisions + recalls, 1e-12), 0.0)
    # precision_recall_curve returns len(thresholds) == len(precisions) - 1
    if len(thresholds) == 0:
        return float(np.median(scores))
    best_idx = int(np.argmax(f1s[:-1]))
    return float(thresholds[best_idx])


def classification_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    y_pred = (scores >= threshold).astype(int)
    n_pos = int(y_true.sum())
    n_neg = len(y_true) - n_pos

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    pr_auc = float(average_precision_score(y_true, scores)) if n_pos > 0 else float("nan")
    roc_auc = float(roc_auc_score(y_true, scores)) if 0 < n_pos < len(y_true) else float("nan")

    return {
        "threshold": float(threshold),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "n_total": len(y_true),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": pr_auc,
        "roc_auc_secondary": roc_auc,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def calibration_assessment(y_true: np.ndarray, scores: np.ndarray, n_bins: int = 10) -> dict:
    """Reliability-curve data + Brier score + a qualitative over/under-
    confidence read. `scores` should be probability-like in [0,1] — for the
    non-probabilistic baseline, pass predict_pseudo_probability(), not
    predict_score(), and note the caveat in the caller.
    """
    scores_clipped = np.clip(scores, 0.0, 1.0)
    brier = float(brier_score_loss(y_true, scores_clipped))
    try:
        observed_freq, mean_predicted = calibration_curve(y_true, scores_clipped, n_bins=n_bins, strategy="quantile")
    except ValueError:
        observed_freq, mean_predicted = calibration_curve(y_true, scores_clipped, n_bins=min(5, n_bins))

    mean_gap = float(np.mean(mean_predicted - observed_freq)) if len(mean_predicted) else float("nan")
    if len(mean_predicted) == 0 or np.isnan(mean_gap):
        verdict = "insufficient data"
    elif mean_gap > 0.03:
        verdict = "overconfident (predicted probabilities systematically higher than observed frequency)"
    elif mean_gap < -0.03:
        verdict = "underconfident (predicted probabilities systematically lower than observed frequency)"
    else:
        verdict = "reasonably calibrated on average"

    return {
        "brier_score": brier,
        "mean_predicted_minus_observed": mean_gap,
        "verdict": verdict,
        "reliability_curve": {
            "mean_predicted": mean_predicted.tolist(),
            "observed_frequency": observed_freq.tolist(),
        },
    }


def false_positive_cost_analysis(confusion: dict) -> dict:
    """A transparent, explicitly synthetic cost-accounting illustration —
    see docs/research/baseline_ml_report.md for the disclaimer. NOT a
    Razorpay economics estimate.
    """
    fp, tp = confusion["fp"], confusion["tp"]
    total_fp_cost = ASSUMED_COST_PER_FALSE_POSITIVE * fp
    fp_per_tp = (fp / tp) if tp > 0 else float("inf")

    sensitivity = []
    for benefit in BENEFIT_PER_TRUE_POSITIVE_SENSITIVITY:
        net_value = benefit * tp - ASSUMED_COST_PER_FALSE_POSITIVE * fp
        sensitivity.append({"assumed_benefit_per_true_positive": benefit, "net_value_units": float(net_value)})

    return {
        "assumed_cost_per_false_positive": ASSUMED_COST_PER_FALSE_POSITIVE,
        "n_false_positives": int(fp),
        "n_true_positives": int(tp),
        "total_fp_cost_units": float(total_fp_cost),
        "false_positives_per_true_positive": float(fp_per_tp),
        "net_value_sensitivity": sensitivity,
        "disclaimer": (
            "assumed_cost_per_false_positive and the benefit-per-true-positive sweep are illustrative "
            "synthetic modeling assumptions chosen to demonstrate the trade-off, not real Razorpay costs."
        ),
    }
