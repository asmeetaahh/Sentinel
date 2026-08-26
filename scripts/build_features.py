#!/usr/bin/env python3
"""
Build the causal feature matrix from the synthetic merchant benchmark.

Reads ONLY data/raw/merchants.csv (merchant_id, signup_date columns only)
and data/raw/daily_observations.csv. Never reads data/scenarios/events.csv
or data/processed/labels.csv.

Usage:
    python scripts/build_features.py
    python scripts/build_features.py --data-dir data

Writes:
    data/processed/features.csv
    data/metadata/feature_manifest.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.build_features import build_features, feature_columns, load_inputs
from ml.features.io_utils import write_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=str, default=str(REPO_ROOT / "data"))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    print("Loading inputs (merchants[merchant_id, signup_date] + daily_observations) ...")
    daily, merchants = load_inputs(data_dir)

    print(f"Building features for {daily['merchant_id'].nunique()} merchants x up to {daily['day_index'].max()+1} days ...")
    features_df = build_features(daily, merchants)

    result = write_features(features_df, data_dir)

    cols = feature_columns(features_df)
    print("Done.")
    print(f"  rows:     {result['n_rows']}")
    print(f"  features: {result['n_features']}")
    print(f"  written:  {result['features_path']}")
    print(f"  manifest: {result['manifest_path']}")

    numeric = features_df[cols].to_numpy(dtype=float)
    n_nan = int(np.isnan(numeric).sum())
    n_inf = int(np.isinf(numeric).sum())
    print(f"  NaNs across all feature cells: {n_nan}")
    print(f"  Infs across all feature cells: {n_inf}")


if __name__ == "__main__":
    main()
