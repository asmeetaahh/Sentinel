"""
The two SHAP plots that materially help inspection — a global importance
bar chart and one illustrative local driver chart. Not a plot per example;
per-example detail belongs in the JSON output for later product use.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_global_importance(global_result: dict, out_path: Path, top_n: int = 20) -> None:
    top = global_result["feature_ranking"][:top_n]
    features = [e["feature"] for e in top][::-1]
    values = [e["mean_abs_shap"] for e in top][::-1]
    groups = [e["group"] for e in top][::-1]

    unique_groups = sorted(set(groups))
    palette = plt.get_cmap("tab10")
    color_by_group = {g: palette(i % 10) for i, g in enumerate(unique_groups)}
    colors = [color_by_group[g] for g in groups]

    fig, ax = plt.subplots(figsize=(8, 0.35 * len(top) + 1.5))
    ax.barh(features, values, color=colors)
    ax.set_xlabel("Mean |SHAP value| (impact on raw Random Forest probability)")
    ax.set_title(f"Global feature importance — top {top_n} (n={global_result['n_rows_explained']} test rows)")

    handles = [plt.Rectangle((0, 0), 1, 1, color=color_by_group[g]) for g in unique_groups]
    ax.legend(handles, unique_groups, loc="lower right", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_local_drivers(explanation_dict: dict, out_path: Path) -> None:
    positive = explanation_dict["drivers"]["top_positive_contributors"]
    negative = explanation_dict["drivers"]["top_negative_contributors"]

    rows = list(reversed(negative)) + list(reversed(positive))
    features = [r["feature"] for r in rows]
    values = [r["shap_value"] for r in rows]
    colors = ["#2471a3" if v < 0 else "#c0392b" for v in values]

    fig, ax = plt.subplots(figsize=(8, 0.4 * len(rows) + 1.5))
    ax.barh(features, values, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("SHAP value (impact on raw Random Forest probability)")
    p = explanation_dict["prediction"]
    ax.set_title(
        f"{explanation_dict['merchant_id']} @ {explanation_dict['as_of_date']} — "
        f"calibrated p={p['model_probability_calibrated']:.3f}, threshold={p['decision_threshold']:.3f}"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
