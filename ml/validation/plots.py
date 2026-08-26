"""
The handful of validation plots that materially help inspection (per the
brief — not a plot for every table). Each function saves one PNG and
returns nothing; failures here should never block the rest of validation.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_growth_vs_risk(pooled: pd.DataFrame, out_path: Path) -> None:
    pooled = pooled.sort_values("gmv_ratio_vs_baseline")
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"risk": "#c0392b", "benign_growth": "#2471a3", "normal": "#7f8c8d"}
    ax.scatter(
        pooled["gmv_ratio_vs_baseline"],
        pooled["chargeback_rate_ratio_vs_baseline"],
        c=[colors.get(c, "#333") for c in pooled["category"]],
        s=80,
    )
    for _, row in pooled.iterrows():
        ax.annotate(row["active_event_type"], (row["gmv_ratio_vs_baseline"], row["chargeback_rate_ratio_vs_baseline"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--")
    ax.axvline(1.0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("GMV vs merchant baseline (ratio)")
    ax.set_ylabel("Chargeback rate vs merchant baseline (ratio)")
    ax.set_title("Growth vs risk: does higher GMV imply higher chargeback rate?")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=9, label=k) for k, c in colors.items()]
    ax.legend(handles=handles)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_label_prevalence_by_horizon(label_check: dict, out_path: Path) -> None:
    horizons = sorted(label_check["by_horizon"].keys())
    rates = [label_check["by_horizon"][h]["positive_rate"] for h in horizons]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar([str(h) for h in horizons], rates, color="#2471a3")
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, r + 0.005, f"{r:.1%}", ha="center", fontsize=9)
    ax.set_xlabel("Prediction horizon (days)")
    ax.set_ylabel("Positive rate (label_elevated_chargeback = 1)")
    ax.set_title("Label prevalence by horizon (own usable-row set)")
    ax.set_ylim(0, max(rates) * 1.3 if rates else 1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_pre_event_trajectory(temporal_check: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for et, data in temporal_check.items():
        offsets = sorted((int(k) for k in data["mean_rolling_chargeback_rate_by_offset"].keys()))
        values = [data["mean_rolling_chargeback_rate_by_offset"][str(o)] for o in offsets]
        ax.plot(offsets, values, label=et, linewidth=1.6)
    ax.axvline(0, color="black", linewidth=1.0, linestyle="--", label="event start")
    ax.set_xlabel("Days relative to event start")
    ax.set_ylabel("Mean 7-day rolling chargeback rate (pooled across instances)")
    ax.set_title("Pre-/post-onset chargeback-rate trajectory by risk event type")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_archetype_positive_rate(archetype_bias_check: dict, out_path: Path) -> None:
    horizons = sorted(archetype_bias_check["by_horizon"].keys())
    archetypes = sorted(archetype_bias_check["by_horizon"][horizons[0]]["positive_rate_by_archetype"].keys())

    fig, ax = plt.subplots(figsize=(10, 5))
    width = 0.25
    x = np.arange(len(archetypes))
    for i, h in enumerate(horizons):
        rates = [archetype_bias_check["by_horizon"][h]["positive_rate_by_archetype"][a] for a in archetypes]
        ax.bar(x + (i - 1) * width, rates, width=width, label=f"{h}d")
    ax.set_xticks(x)
    ax.set_xticklabels(archetypes, rotation=30, ha="right")
    ax.set_ylabel("Positive rate")
    ax.set_title("Label positive rate by archetype and horizon")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
