"""
Application state: loads the benchmark tables, the model artifact, and the
SHAP explainer exactly ONCE at process startup, via FastAPI's lifespan
context manager. Every request reuses this shared, read-only state rather
than re-reading CSVs or reconstructing the SHAP explainer per call.

This module intentionally contains no HTTP-specific code — it is a thin
loader around the already-validated ml.modeling / ml.explainability
packages, per the "do not duplicate the research pipeline" instruction.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from ml.explainability import artifact as artifact_module
from ml.explainability import shap_engine
from ml.explainability.feature_metadata import load_feature_metadata
from ml.modeling import datasets


@dataclass
class AppState:
    merchants: pd.DataFrame
    daily_observations: pd.DataFrame
    features: pd.DataFrame
    labels: pd.DataFrame
    feature_columns: list[str]
    feature_metadata_by_name: dict
    artifact: artifact_module.LoadedArtifact
    explainer: object  # shap.TreeExplainer


_STATE: AppState | None = None


def load_state() -> AppState:
    """Idempotent: safe to call multiple times (e.g. across test modules);
    only loads once per process.
    """
    global _STATE
    if _STATE is not None:
        return _STATE

    tables = datasets.load_raw_tables()  # {"features", "labels", "merchants" (trimmed)} — reused for features/labels
    feature_cols = datasets.load_feature_columns()
    daily_observations = pd.read_csv(REPO_ROOT / "data" / "raw" / "daily_observations.csv", parse_dates=["date"])

    # Full merchant table, loaded separately from tables["merchants"] (which
    # ml.modeling.datasets trims to merchant_id/archetype/business_tier).
    # Services decide what subset of columns to expose — the ml-internal
    # baseline_* ground-truth columns are never surfaced via the API; see
    # backend/services/merchant_service.py.
    merchants_full = pd.read_csv(datasets.MERCHANTS_PATH, parse_dates=["signup_date"])

    loaded_artifact = artifact_module.load_artifact()
    explainer = shap_engine.build_explainer(loaded_artifact.base_random_forest)
    metadata_by_name = load_feature_metadata()

    _STATE = AppState(
        merchants=merchants_full,
        daily_observations=daily_observations,
        features=tables["features"],
        labels=tables["labels"],
        feature_columns=feature_cols,
        feature_metadata_by_name=metadata_by_name,
        artifact=loaded_artifact,
        explainer=explainer,
    )
    return _STATE


def reset_state_for_tests() -> None:
    """Test-only: forces a fresh load on next load_state() call."""
    global _STATE
    _STATE = None
