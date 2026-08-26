"""
Global feature importance from SHAP, aggregated across a representative
held-out evaluation sample (the merchant-level, temporal-cutoff-respecting
normal test split for the 30-day horizon — the exact same split used in
the baseline ML evaluation, never train data).

This is diagnostic/reporting output only — per the task brief, it is never
used here to rewrite the model or select features.
"""

from __future__ import annotations

import numpy as np

from .feature_metadata import metadata_for
from .shap_engine import ShapResult


def global_feature_importance(shap_result: ShapResult, feature_columns: list[str], metadata_by_name: dict) -> dict:
    mean_abs_shap = np.abs(shap_result.shap_values).mean(axis=0)
    mean_signed_shap = shap_result.shap_values.mean(axis=0)

    ranking = sorted(
        [
            {
                "feature": feature_columns[i],
                "group": metadata_for(feature_columns[i], metadata_by_name)["group"],
                "mean_abs_shap": float(mean_abs_shap[i]),
                "mean_signed_shap": float(mean_signed_shap[i]),
            }
            for i in range(len(feature_columns))
        ],
        key=lambda d: -d["mean_abs_shap"],
    )
    for rank, entry in enumerate(ranking, start=1):
        entry["rank"] = rank

    group_importance: dict[str, float] = {}
    for entry in ranking:
        group_importance[entry["group"]] = group_importance.get(entry["group"], 0.0) + entry["mean_abs_shap"]
    group_ranking = sorted(
        [{"group": g, "summed_mean_abs_shap": v} for g, v in group_importance.items()],
        key=lambda d: -d["summed_mean_abs_shap"],
    )

    return {
        "n_rows_explained": int(shap_result.shap_values.shape[0]),
        "feature_ranking": ranking,
        "group_ranking": group_ranking,
        "max_reconstruction_error": shap_result.max_abs_reconstruction_error,
        "faithful": shap_result.faithful,
    }
