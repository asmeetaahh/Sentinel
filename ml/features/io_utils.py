"""
Persisting the feature matrix and its manifest to disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .build_features import build_feature_manifest_df, feature_columns


def write_features(features_df: pd.DataFrame, data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    processed_dir = data_dir / "processed"
    metadata_dir = data_dir / "metadata"
    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    features_path = processed_dir / "features.csv"
    manifest_path = metadata_dir / "feature_manifest.json"

    features_df.to_csv(features_path, index=False)

    manifest_df = build_feature_manifest_df()
    cols = feature_columns(features_df)
    manifest = {
        "n_features": len(cols),
        "n_rows": len(features_df),
        "feature_columns": cols,
        "groups": manifest_df.groupby("group").size().to_dict() if len(manifest_df) else {},
        "features": manifest_df.to_dict(orient="records"),
        "leakage_guarantees": [
            "Only merchants.csv[merchant_id, signup_date] and daily_observations.csv were read.",
            "events.csv and labels.csv were never loaded by this pipeline.",
            "Every feature is a trailing (ending at t, inclusive) or expanding (day_index<=t) function.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    return {"features_path": str(features_path), "manifest_path": str(manifest_path), "n_features": len(cols), "n_rows": len(features_df)}
