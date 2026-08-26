"""
Post-hoc failure analysis: where do false positives/negatives concentrate?

This is diagnostic use of ground-truth scenario metadata (events.csv) to
EXPLAIN model errors after predictions are made — not a model feature. That
distinction matters: PROJECT_CONTEXT.md forbids scenario metadata as a
feature (that would be leakage), but using it to audit *why* a model got
something wrong is standard, necessary evaluation practice, identical in
spirit to how dataset validation used it to audit the generator itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.validation.checks import tag_active_event  # reused, not reimplemented


def _tag_frame_with_events(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    tagged_input = frame[["merchant_id", "day_index"]].copy()
    tagged_input["date"] = frame["as_of_date"].values
    tagged = tag_active_event(tagged_input, events)
    frame = frame.copy()
    frame["active_event_type"] = tagged["active_event_type"].values
    frame["active_event_category"] = tagged["active_event_category"].values
    return frame


def analyze_errors(
    frame: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    events: pd.DataFrame,
    volume_feature: str = "transaction_count_level_28d",
) -> dict:
    df = frame.copy().reset_index(drop=True)
    df["y_true"] = y_true
    df["y_pred"] = y_pred
    df = _tag_frame_with_events(df, events)

    volume_median = df[volume_feature].median()
    df["volume_bucket"] = np.where(df[volume_feature] < volume_median, "low_volume", "higher_volume")

    df["error_type"] = np.select(
        [
            (df["y_true"] == 0) & (df["y_pred"] == 1),
            (df["y_true"] == 1) & (df["y_pred"] == 0),
            (df["y_true"] == 1) & (df["y_pred"] == 1),
            (df["y_true"] == 0) & (df["y_pred"] == 0),
        ],
        ["false_positive", "false_negative", "true_positive", "true_negative"],
        default="unknown",
    )

    def breakdown(sub_df: pd.DataFrame, by: str) -> dict:
        if sub_df.empty:
            return {}
        return sub_df[by].value_counts(normalize=False).to_dict()

    def rate_breakdown(error_label: str, denom_mask, by: str) -> dict:
        """Rate = (rows with this error AND this category) / (all rows in
        this category) — answers 'is this category over-represented among
        errors', not just 'how many errors are in this category'.
        """
        denom = df[denom_mask]
        if denom.empty:
            return {}
        numer = denom[denom["error_type"] == error_label]
        counts_denom = denom[by].value_counts()
        counts_numer = numer[by].value_counts()
        return {
            cat: {
                "rate": float(counts_numer.get(cat, 0) / counts_denom[cat]),
                "n_errors": int(counts_numer.get(cat, 0)),
                "n_total_in_category": int(counts_denom[cat]),
            }
            for cat in counts_denom.index
        }

    fp = df[df["error_type"] == "false_positive"]
    fn = df[df["error_type"] == "false_negative"]

    negatives_mask = df["y_true"] == 0
    positives_mask = df["y_true"] == 1

    return {
        "n_false_positives": int(len(fp)),
        "n_false_negatives": int(len(fn)),
        "false_positive_breakdown": {
            "by_active_event_type": breakdown(fp, "active_event_type"),
            "by_active_event_category": breakdown(fp, "active_event_category"),
            "by_archetype": breakdown(fp, "archetype"),
            "by_volume_bucket": breakdown(fp, "volume_bucket"),
        },
        "false_negative_breakdown": {
            "by_active_event_type": breakdown(fn, "active_event_type"),
            "by_active_event_category": breakdown(fn, "active_event_category"),
            "by_archetype": breakdown(fn, "archetype"),
            "by_volume_bucket": breakdown(fn, "volume_bucket"),
        },
        "false_positive_rate_by_active_event_type_among_negatives": rate_breakdown("false_positive", negatives_mask, "active_event_type"),
        "false_negative_rate_by_active_event_type_among_positives": rate_breakdown("false_negative", positives_mask, "active_event_type"),
        "false_positive_rate_by_archetype_among_negatives": rate_breakdown("false_positive", negatives_mask, "archetype"),
        "false_negative_rate_by_archetype_among_positives": rate_breakdown("false_negative", positives_mask, "archetype"),
    }
