"""
Loading the EXACT saved provisional Random Forest / 30-day artifact — never
retraining, never silently substituting a different model.

Artifact identity (see docs/architecture/explainability.md and
docs/research/baseline_ml_report.md §E.1 for how it was produced):
    data/metadata/modeling/artifacts/random_forest_calibrated_30d.joblib
    data/metadata/modeling/artifacts/random_forest_calibrated_30d_config.json

The saved object is an sklearn.calibration.CalibratedClassifierCV (sigmoid
method, wrapping a FrozenEstimator around an already-fit
RandomForestClassifier — see ml/modeling/calibration.py). Two related but
distinct things can be explained here, and this module is explicit about
which is which everywhere downstream:

  - calibrated_pipeline.predict_proba(X)[:, 1] — the FINAL, calibrated
    probability the artifact was built to produce; this is the "verified
    prediction" against the artifact's own decision_threshold.
  - base_random_forest.predict_proba(X)[:, 1] — the underlying tree
    ensemble's raw probability, BEFORE the sigmoid calibration layer.

SHAP (TreeExplainer) is computed against the base Random Forest, because
it is the tree ensemble whose exact, additive Shapley decomposition SHAP
guarantees — the sigmoid calibration layer sitting on top is a 2-parameter
monotonic rescaling with no per-feature structure for SHAP to decompose.
Because it is monotonic, it changes neither the ranking of examples nor
the sign/relative ordering of feature contributions (this was already
established empirically in the calibration report — calibrated and
uncalibrated RF have identical precision/recall/F1/PR-AUC because ranking
is preserved). It DOES change the numeric probability value. Every
explanation produced by this package therefore reports both numbers
side by side rather than conflating them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier

from .config import ARTIFACT_CONFIG_PATH, ARTIFACT_PATH, HORIZON_DAYS


@dataclass
class LoadedArtifact:
    calibrated_pipeline: CalibratedClassifierCV
    base_random_forest: RandomForestClassifier
    feature_columns: list[str]
    decision_threshold: float
    horizon_days: int
    config: dict
    artifact_path: Path
    config_path: Path


def _extract_base_random_forest(calibrated_pipeline: CalibratedClassifierCV) -> RandomForestClassifier:
    if len(calibrated_pipeline.calibrated_classifiers_) != 1:
        raise ValueError(
            "Expected exactly one calibrated classifier (prefit/FrozenEstimator calibration produces one); "
            f"found {len(calibrated_pipeline.calibrated_classifiers_)}. Refusing to guess which one to explain."
        )
    calibrated_classifier = calibrated_pipeline.calibrated_classifiers_[0]
    frozen_estimator = calibrated_classifier.estimator
    base = getattr(frozen_estimator, "estimator", frozen_estimator)
    if not isinstance(base, RandomForestClassifier):
        raise TypeError(
            f"Expected a RandomForestClassifier inside the artifact, found {type(base)}. "
            "This explainability module is built for the provisional Random Forest candidate only."
        )
    return base


def load_artifact(
    artifact_path: Path = ARTIFACT_PATH,
    config_path: Path = ARTIFACT_CONFIG_PATH,
    expected_horizon_days: int = HORIZON_DAYS,
) -> LoadedArtifact:
    if not artifact_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}. Run scripts/evaluate_calibration.py first.")
    if not config_path.exists():
        raise FileNotFoundError(f"Artifact config not found: {config_path}.")

    config = json.loads(config_path.read_text())

    if config["horizon_days"] != expected_horizon_days:
        raise ValueError(
            f"Artifact config horizon_days={config['horizon_days']} does not match the expected "
            f"{expected_horizon_days}-day provisional candidate. Refusing to proceed silently."
        )

    calibrated_pipeline = joblib.load(artifact_path)
    if not isinstance(calibrated_pipeline, CalibratedClassifierCV):
        raise TypeError(f"Expected a CalibratedClassifierCV artifact, found {type(calibrated_pipeline)}.")

    base_random_forest = _extract_base_random_forest(calibrated_pipeline)

    feature_columns = config["feature_columns_in_order"]
    if base_random_forest.n_features_in_ != len(feature_columns):
        raise ValueError(
            f"Artifact's fitted Random Forest expects {base_random_forest.n_features_in_} features, "
            f"but the config lists {len(feature_columns)} feature_columns_in_order. Refusing to proceed."
        )

    return LoadedArtifact(
        calibrated_pipeline=calibrated_pipeline,
        base_random_forest=base_random_forest,
        feature_columns=feature_columns,
        decision_threshold=config["decision_threshold"],
        horizon_days=config["horizon_days"],
        config=config,
        artifact_path=artifact_path,
        config_path=config_path,
    )
