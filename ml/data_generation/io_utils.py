"""
Persisting a GeneratedDataset to disk under data/, matching the existing
repo layout (data/raw, data/scenarios, data/processed, data/metadata).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .archetypes import ARCHETYPE_PARAMS
from .config import LABEL_HORIZONS_DAYS
from .generator import GeneratedDataset
from .schema import as_json_schema

GENERATOR_VERSION = "0.1.0"


def write_dataset(dataset: GeneratedDataset, data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    raw_dir = data_dir / "raw"
    scenarios_dir = data_dir / "scenarios"
    processed_dir = data_dir / "processed"
    metadata_dir = data_dir / "metadata"
    for d in (raw_dir, scenarios_dir, processed_dir, metadata_dir):
        d.mkdir(parents=True, exist_ok=True)

    merchants_path = raw_dir / "merchants.csv"
    daily_path = raw_dir / "daily_observations.csv"
    events_path = scenarios_dir / "events.csv"
    labels_path = processed_dir / "labels.csv"
    schema_path = metadata_dir / "schema.json"
    manifest_path = metadata_dir / "generation_manifest.json"

    dataset.merchants.to_csv(merchants_path, index=False)
    dataset.daily_observations.to_csv(daily_path, index=False)
    dataset.events.to_csv(events_path, index=False)
    dataset.labels.to_csv(labels_path, index=False)

    schema_path.write_text(json.dumps(as_json_schema(), indent=2))

    archetype_counts = dataset.merchants["archetype"].value_counts().to_dict()
    event_type_counts = (
        dataset.events["event_type"].value_counts().to_dict() if len(dataset.events) else {}
    )
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": dataset.seed,
        "n_merchants": dataset.n_merchants,
        "n_days": dataset.n_days,
        "start_date": dataset.start_date.isoformat(),
        "end_date": (
            dataset.daily_observations["date"].max().isoformat()
            if len(dataset.daily_observations)
            else None
        ),
        "archetypes": sorted(ARCHETYPE_PARAMS.keys()),
        "archetype_merchant_counts": archetype_counts,
        "label_horizons_days": LABEL_HORIZONS_DAYS,
        "row_counts": {
            "merchants": len(dataset.merchants),
            "daily_observations": len(dataset.daily_observations),
            "events": len(dataset.events),
            "labels": len(dataset.labels),
        },
        "event_type_counts": event_type_counts,
        "disclaimer": (
            "All values in this dataset are synthetically generated for "
            "benchmark construction. None are derived from real Razorpay, "
            "merchant, or industry statistics. See docs/data_generation.md."
        ),
        "files": {
            "merchants": str(merchants_path.relative_to(data_dir.parent)),
            "daily_observations": str(daily_path.relative_to(data_dir.parent)),
            "events": str(events_path.relative_to(data_dir.parent)),
            "labels": str(labels_path.relative_to(data_dir.parent)),
            "schema": str(schema_path.relative_to(data_dir.parent)),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest
