"""
Plots that materially help interpretation — not one per table. See
docs/research/baseline_ml_report.md for how each is used.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve


def plot_pr_curves_by_horizon(pr_data: dict, out_path: Path) -> None:
    """pr_data: {horizon: {model_name: (y_true, scores, positive_rate)}}"""
    horizons = sorted(pr_data.keys())
    fig, axes = plt.subplots(1, len(horizons), figsize=(6 * len(horizons), 5), sharey=True)
    if len(horizons) == 1:
        axes = [axes]
    for ax, h in zip(axes, horizons):
        for model_name, (y_true, scores, pos_rate) in pr_data[h].items():
            precision, recall, _ = precision_recall_curve(y_true, scores)
            ax.plot(recall, precision, label=model_name, linewidth=1.6)
        ax.axhline(pos_rate, color="gray", linestyle="--", linewidth=1, label="positive rate (random)")
        ax.set_xlabel("Recall")
        ax.set_title(f"{h}-day horizon")
        ax.set_ylim(0, 1.02)
        ax.set_xlim(0, 1.02)
    axes[0].set_ylabel("Precision")
    axes[-1].legend(fontsize=8, loc="upper right")
    fig.suptitle("Precision-Recall curves by model and horizon (test set)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_calibration_by_horizon(calibration_data: dict, out_path: Path) -> None:
    """calibration_data: {horizon: {model_name: reliability_curve dict}}"""
    horizons = sorted(calibration_data.keys())
    fig, axes = plt.subplots(1, len(horizons), figsize=(6 * len(horizons), 5), sharey=True)
    if len(horizons) == 1:
        axes = [axes]
    for ax, h in zip(axes, horizons):
        ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, label="perfectly calibrated")
        for model_name, curve in calibration_data[h].items():
            ax.plot(curve["mean_predicted"], curve["observed_frequency"], marker="o", markersize=4, label=model_name, linewidth=1.4)
        ax.set_xlabel("Mean predicted probability")
        ax.set_title(f"{h}-day horizon")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("Observed frequency")
    axes[-1].legend(fontsize=8, loc="upper left")
    fig.suptitle("Calibration (reliability curves) by model and horizon (test set)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_warning_lead_time_distribution(lead_time_data: dict, out_path: Path) -> None:
    """lead_time_data: {horizon: {model_name: [lead_time_days, ...]}}"""
    horizons = sorted(lead_time_data.keys())
    fig, axes = plt.subplots(1, len(horizons), figsize=(6 * len(horizons), 5), sharey=True)
    if len(horizons) == 1:
        axes = [axes]
    for ax, h in zip(axes, horizons):
        model_names = list(lead_time_data[h].keys())
        data = [lead_time_data[h][m] if lead_time_data[h][m] else [np.nan] for m in model_names]
        ax.boxplot(data, tick_labels=model_names, showmeans=True)
        ax.set_title(f"{h}-day horizon")
        ax.tick_params(axis="x", rotation=30)
        ax.axhline(h, color="red", linestyle=":", linewidth=1, label="max possible (= horizon)")
    axes[0].set_ylabel("Warning lead time (days), early-warning episodes only")
    axes[-1].legend(fontsize=8)
    fig.suptitle("Warning lead-time distribution by model and horizon")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_model_horizon_comparison(comparison_rows: list[dict], metric: str, metric_label: str, out_path: Path) -> None:
    models = sorted({r["model"] for r in comparison_rows})
    horizons = sorted({r["horizon"] for r in comparison_rows})
    x = np.arange(len(horizons))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, model in enumerate(models):
        values = [next((r[metric] for r in comparison_rows if r["model"] == model and r["horizon"] == h), np.nan) for h in horizons]
        ax.bar(x + i * width, values, width=width, label=model)
    ax.set_xticks(x + width * (len(models) - 1) / 2)
    ax.set_xticklabels([f"{h}d" for h in horizons])
    ax.set_ylabel(metric_label)
    ax.set_title(f"{metric_label} by model and horizon (test set)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_error_breakdown(fp_breakdown: dict, fn_breakdown: dict, title: str, out_path: Path) -> None:
    categories = sorted(set(fp_breakdown) | set(fn_breakdown))
    fp_vals = [fp_breakdown.get(c, 0) for c in categories]
    fn_vals = [fn_breakdown.get(c, 0) for c in categories]

    x = np.arange(len(categories))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, fp_vals, width=width, label="False Positives", color="#c0392b")
    ax.bar(x + width / 2, fn_vals, width=width, label="False Negatives", color="#2471a3")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
