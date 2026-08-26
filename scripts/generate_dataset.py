#!/usr/bin/env python3
"""
Regenerate the Sentinel synthetic merchant benchmark from scratch.

Usage:
    python scripts/generate_dataset.py
    python scripts/generate_dataset.py --merchants 50 --days 180 --seed 42
    python scripts/generate_dataset.py --merchants 500 --days 365 --seed 42

Writes:
    data/raw/merchants.csv
    data/raw/daily_observations.csv
    data/scenarios/events.csv
    data/processed/labels.csv
    data/metadata/schema.json
    data/metadata/generation_manifest.json
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.data_generation.config import DEFAULT_N_DAYS, DEFAULT_N_MERCHANTS, DEFAULT_SEED, DEFAULT_START_DATE
from ml.data_generation.generator import generate_dataset
from ml.data_generation.io_utils import write_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--merchants", type=int, default=DEFAULT_N_MERCHANTS, help="Number of merchants to generate.")
    parser.add_argument("--days", type=int, default=DEFAULT_N_DAYS, help="Number of days per merchant.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed (reproducibility).")
    parser.add_argument(
        "--start-date",
        type=str,
        default=DEFAULT_START_DATE.isoformat(),
        help="Synthetic anchor start date, YYYY-MM-DD.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(REPO_ROOT / "data"),
        help="Output data directory (must contain/receive raw/, scenarios/, processed/, metadata/).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start_date = date.fromisoformat(args.start_date)

    print(f"Generating dataset: {args.merchants} merchants x {args.days} days, seed={args.seed} ...")
    dataset = generate_dataset(
        seed=args.seed,
        n_merchants=args.merchants,
        n_days=args.days,
        start_date=start_date,
    )

    manifest = write_dataset(dataset, data_dir=Path(args.data_dir))

    print("Done.")
    print(f"  merchants:          {manifest['row_counts']['merchants']} rows")
    print(f"  daily_observations: {manifest['row_counts']['daily_observations']} rows")
    print(f"  events:             {manifest['row_counts']['events']} rows")
    print(f"  labels:             {manifest['row_counts']['labels']} rows")
    print(f"  written under:      {args.data_dir}")


if __name__ == "__main__":
    main()
