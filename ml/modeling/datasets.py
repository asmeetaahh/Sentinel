"""
Assembling model-ready (X, y) datasets from the already-built feature and
label tables.

Leakage discipline:
  - Join key is exactly (merchant_id, day_index) — as_of_date in labels.csv
    corresponds 1:1 to date/day_index in features.csv; joining on day_index
    (an int) avoids any dtype/format mismatch risk from date parsing.
  - The feature matrix X is restricted to the columns listed in
    data/metadata/feature_manifest.json — nothing else from either table
    (not day_index, not merchant_id, not any labels.csv column) is ever
    passed to a model as a feature.
  - Splitting into train/val/test happens on the merchant_id list
    (splits.py), then rows are filtered to match — never split by row.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import FEATURE_MANIFEST_PATH, FEATURES_PATH, LABELS_PATH, MERCHANTS_PATH, TEMPORAL_CUTOFF_DAY_INDEX


def load_feature_columns() -> list[str]:
    manifest = json.loads(Path(FEATURE_MANIFEST_PATH).read_text())
    return manifest["feature_columns"]


def load_raw_tables() -> dict[str, pd.DataFrame]:
    features = pd.read_csv(FEATURES_PATH, parse_dates=["date"])
    labels = pd.read_csv(LABELS_PATH, parse_dates=["as_of_date"])
    merchants = pd.read_csv(MERCHANTS_PATH)[["merchant_id", "archetype", "business_tier"]]
    return {"features": features, "labels": labels, "merchants": merchants}


def build_horizon_frame(tables: dict[str, pd.DataFrame], horizon_days: int) -> pd.DataFrame:
    """One row per (merchant_id, day_index) for this horizon: the 55
    features, the classification target, the regression target, and a
    handful of ID/context columns (never fed to a model) for splitting,
    analysis, and reporting.
    """
    feature_cols = load_feature_columns()
    features, labels, merchants = tables["features"], tables["labels"], tables["merchants"]

    lab = labels[labels["horizon_days"] == horizon_days]
    merged = lab.merge(
        features,
        on=["merchant_id", "day_index"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_feat"),
    )
    merged = merged.merge(merchants, on="merchant_id", how="left")

    context_cols = [
        "merchant_id",
        "archetype",
        "business_tier",
        "as_of_date",
        "day_index",
        "label_elevated_chargeback",
        "future_chargeback_amount",
        "baseline_daily_chargeback_amount_trailing",  # naive regression baseline input only, see regression.py
    ]
    out = merged[context_cols + feature_cols].copy()
    return out


def apply_merchant_split(frame: pd.DataFrame, split_df: pd.DataFrame) -> pd.DataFrame:
    merged = frame.merge(split_df[["merchant_id", "split"]], on="merchant_id", how="left")
    assert merged["split"].notna().all(), "some merchants in the feature frame are missing from the split"
    return merged


def train_val_test_frames(frame_with_split: pd.DataFrame, temporal_cutoff: int = TEMPORAL_CUTOFF_DAY_INDEX) -> dict[str, pd.DataFrame]:
    """Returns train/val/normal_test/stress_test frames.

    train, val, normal_test: day_index < temporal_cutoff (the "early" period).
    stress_test: SAME test merchants, day_index >= temporal_cutoff (the
    "late" period the model never saw during training, from any merchant).
    """
    early = frame_with_split[frame_with_split["day_index"] < temporal_cutoff]
    late = frame_with_split[frame_with_split["day_index"] >= temporal_cutoff]

    return {
        "train": early[early["split"] == "train"].reset_index(drop=True),
        "val": early[early["split"] == "val"].reset_index(drop=True),
        "normal_test": early[early["split"] == "test"].reset_index(drop=True),
        "stress_test": late[late["split"] == "test"].reset_index(drop=True),
    }


def xy(frame: pd.DataFrame, feature_cols: list[str], target_col: str = "label_elevated_chargeback"):
    X = frame[feature_cols].to_numpy(dtype=float)
    y = frame[target_col].to_numpy()
    return X, y
