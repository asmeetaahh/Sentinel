"""
Configuration for Sentinel's SHAP-based explainability layer.

This module explains an EXISTING, already-trained/calibrated artifact — it
never trains, retrains, or searches over models. See artifact.py for the
exact artifact identity.
"""

from __future__ import annotations

from pathlib import Path

ARTIFACT_DIR = Path("data/metadata/modeling/artifacts")
ARTIFACT_PATH = ARTIFACT_DIR / "random_forest_calibrated_30d.joblib"
ARTIFACT_CONFIG_PATH = ARTIFACT_DIR / "random_forest_calibrated_30d_config.json"

FEATURE_MANIFEST_PATH = Path("data/metadata/feature_manifest.json")

OUTPUT_DIR = Path("data/metadata/explainability")
PLOTS_DIR = OUTPUT_DIR / "plots"

HORIZON_DAYS = 30  # must match the artifact config's horizon_days — verified at load time, not assumed

# Positive ("elevated chargeback risk") class index in sklearn's
# predict_proba / SHAP's per-class output.
POSITIVE_CLASS_INDEX = 1

# Faithfulness check: sum(shap_values) + expected_value must reconstruct
# the explained model's raw output within this absolute tolerance.
# TreeSHAP is an exact method for tree ensembles, so this is a tight
# numerical-precision check, not a loose approximation allowance.
FAITHFULNESS_ABS_TOLERANCE = 1e-4

# How many top positive / negative contributors to surface per local
# explanation (kept small deliberately — this feeds a future product
# surface, not a dump of all 55 features).
TOP_K_CONTRIBUTORS = 6

# Sample size for the global explanation pass over the held-out test set.
# None = use the full normal test set for this horizon (960 rows at the
# 50x180 benchmark scale — small enough to run in full).
GLOBAL_EXPLANATION_MAX_ROWS = None
