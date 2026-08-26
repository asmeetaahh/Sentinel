"""
Connects SHAP feature names to the existing feature manifest
(data/metadata/feature_manifest.json, produced by ml/features/) so every
displayed driver carries its group, definition, window, and kind — never
re-derived or guessed from the feature's name.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import FEATURE_MANIFEST_PATH


def load_feature_metadata(path: Path = FEATURE_MANIFEST_PATH) -> dict[str, dict]:
    manifest = json.loads(Path(path).read_text())
    by_name = {}
    for entry in manifest["features"]:
        by_name[entry["name"]] = {
            "group": entry["group"],
            "definition": entry["definition"],
            "window": entry["window"],
            "kind": entry["kind"],
            "source_columns": entry["source_columns"],
        }
    return by_name


def metadata_for(feature_name: str, metadata_by_name: dict[str, dict]) -> dict:
    """Never fabricates metadata: if a feature is missing from the
    manifest (shouldn't happen for the 55 causal features, but the
    artifact's own column list is the source of truth for what's actually
    fed to the model), returns an explicit placeholder rather than
    inventing a definition.
    """
    if feature_name in metadata_by_name:
        return metadata_by_name[feature_name]
    return {
        "group": "unknown",
        "definition": "No manifest entry found for this feature — metadata unavailable, not fabricated.",
        "window": None,
        "kind": "unknown",
        "source_columns": [],
    }
