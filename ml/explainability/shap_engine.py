"""
Core SHAP computation: builds a TreeExplainer for the artifact's base
Random Forest and computes exact Shapley-value decompositions.

Why TreeExplainer: the explained model (RandomForestClassifier) is a tree
ensemble, and TreeSHAP computes EXACT Shapley values for tree ensembles in
polynomial time — no sampling, no approximation of the attribution itself
(see https://arxiv.org/abs/1802.03888). This is why the additivity check
in verify_faithfulness() below uses a tight numerical tolerance rather than
a loose one: any material deviation would indicate a real bug (e.g. a
class-index mix-up), not expected approximation error.

feature_perturbation="tree_path_dependent" (SHAP's default for
TreeExplainer, used here explicitly rather than left implicit) uses the
training-data statistics already embedded in the trees' internal node
sample weights, so no separate background dataset needs to be chosen or
justified.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier

from .config import FAITHFULNESS_ABS_TOLERANCE, POSITIVE_CLASS_INDEX


@dataclass
class ShapResult:
    shap_values: np.ndarray  # (n_samples, n_features), positive class only
    base_value: float  # SHAP's expected_value for the positive class
    raw_probability: np.ndarray  # (n_samples,), base_random_forest.predict_proba(X)[:, 1]
    reconstructed_probability: np.ndarray  # base_value + shap_values.sum(axis=1)
    max_abs_reconstruction_error: float
    faithful: bool


def build_explainer(base_random_forest: RandomForestClassifier) -> shap.TreeExplainer:
    return shap.TreeExplainer(base_random_forest, feature_perturbation="tree_path_dependent")


def compute_shap_values(explainer: shap.TreeExplainer, base_random_forest: RandomForestClassifier, X: np.ndarray) -> ShapResult:
    if X.ndim != 2:
        raise ValueError(f"Expected a 2D feature matrix, got shape {X.shape}")

    raw_shap = explainer.shap_values(X)
    # shap>=0.45 for multiclass/binary sklearn trees returns
    # (n_samples, n_features, n_classes); older versions return a list of
    # per-class (n_samples, n_features) arrays. Handle both explicitly
    # rather than assuming one shape.
    if isinstance(raw_shap, list):
        shap_values = raw_shap[POSITIVE_CLASS_INDEX]
        expected_value = explainer.expected_value[POSITIVE_CLASS_INDEX]
    elif raw_shap.ndim == 3:
        shap_values = raw_shap[:, :, POSITIVE_CLASS_INDEX]
        expected_value = explainer.expected_value[POSITIVE_CLASS_INDEX]
    else:
        # Binary model explained with a single-output shape — SHAP values
        # already correspond to the positive class by convention.
        shap_values = raw_shap
        expected_value = float(np.asarray(explainer.expected_value).reshape(-1)[POSITIVE_CLASS_INDEX])

    raw_probability = base_random_forest.predict_proba(X)[:, POSITIVE_CLASS_INDEX]
    reconstructed = float(expected_value) + shap_values.sum(axis=1)
    max_error = float(np.max(np.abs(reconstructed - raw_probability))) if len(raw_probability) else 0.0

    return ShapResult(
        shap_values=shap_values,
        base_value=float(expected_value),
        raw_probability=raw_probability,
        reconstructed_probability=reconstructed,
        max_abs_reconstruction_error=max_error,
        faithful=max_error <= FAITHFULNESS_ABS_TOLERANCE,
    )
