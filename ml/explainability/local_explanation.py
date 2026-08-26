"""
Structured, deterministic per-row explanations — the object a future
product layer would turn into language like "chargeback velocity is
contributing materially to elevated risk." Nothing here generates prose;
every field is a verified number or a manifest-sourced string.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .artifact import LoadedArtifact
from .config import TOP_K_CONTRIBUTORS
from .feature_metadata import metadata_for
from .shap_engine import ShapResult


def _direction(shap_value: float) -> str:
    if shap_value > 0:
        return "increases_risk"
    if shap_value < 0:
        return "decreases_risk"
    return "neutral"


def _driver(feature_name: str, value: float, shap_value: float, metadata_by_name: dict) -> dict:
    meta = metadata_for(feature_name, metadata_by_name)
    return {
        "feature": feature_name,
        "group": meta["group"],
        "definition": meta["definition"],
        "window": meta["window"],
        "kind": meta["kind"],
        "value": float(value),
        "shap_value": float(shap_value),
        "direction": _direction(shap_value),
    }


@dataclass
class LocalExplanation:
    merchant_id: str
    as_of_date: str
    day_index: int
    horizon_days: int
    model_probability_calibrated: float
    model_probability_raw_rf: float
    decision_threshold: float
    predicted_positive: bool
    shap_base_value: float
    shap_reconstructed_probability: float
    shap_reconstruction_error: float
    faithful: bool
    top_positive_contributors: list = field(default_factory=list)
    top_negative_contributors: list = field(default_factory=list)
    all_contributors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "as_of_date": self.as_of_date,
            "day_index": self.day_index,
            "horizon_days": self.horizon_days,
            "prediction": {
                "model_probability_calibrated": self.model_probability_calibrated,
                "model_probability_raw_rf": self.model_probability_raw_rf,
                "decision_threshold": self.decision_threshold,
                "predicted_positive": self.predicted_positive,
                "note": (
                    "model_probability_calibrated is the artifact's official output (used against "
                    "decision_threshold). SHAP explains model_probability_raw_rf, the pre-calibration "
                    "Random Forest score — see docs/architecture/explainability.md."
                ),
            },
            "faithfulness": {
                "shap_base_value": self.shap_base_value,
                "shap_reconstructed_probability": self.shap_reconstructed_probability,
                "reconstruction_error": self.shap_reconstruction_error,
                "faithful": self.faithful,
            },
            "drivers": {
                "top_positive_contributors": self.top_positive_contributors,
                "top_negative_contributors": self.top_negative_contributors,
            },
            "all_contributors": self.all_contributors,
        }


def explain_row(
    row_index: int,
    X_row: np.ndarray,
    shap_result: ShapResult,
    feature_columns: list[str],
    metadata_by_name: dict,
    artifact: LoadedArtifact,
    calibrated_probability: float,
    merchant_id: str,
    as_of_date: str,
    day_index: int,
    top_k: int = TOP_K_CONTRIBUTORS,
) -> LocalExplanation:
    shap_row = shap_result.shap_values[row_index]

    contributors = [
        _driver(feature_columns[i], X_row[i], shap_row[i], metadata_by_name) for i in range(len(feature_columns))
    ]
    contributors_sorted_by_magnitude = sorted(contributors, key=lambda d: -abs(d["shap_value"]))

    positive = sorted([c for c in contributors if c["shap_value"] > 0], key=lambda d: -d["shap_value"])[:top_k]
    negative = sorted([c for c in contributors if c["shap_value"] < 0], key=lambda d: d["shap_value"])[:top_k]

    raw_rf_probability = float(shap_result.raw_probability[row_index])

    return LocalExplanation(
        merchant_id=merchant_id,
        as_of_date=as_of_date,
        day_index=int(day_index),
        horizon_days=artifact.horizon_days,
        model_probability_calibrated=float(calibrated_probability),
        model_probability_raw_rf=raw_rf_probability,
        decision_threshold=artifact.decision_threshold,
        predicted_positive=bool(calibrated_probability >= artifact.decision_threshold),
        shap_base_value=shap_result.base_value,
        shap_reconstructed_probability=float(shap_result.reconstructed_probability[row_index]),
        shap_reconstruction_error=float(abs(shap_result.reconstructed_probability[row_index] - raw_rf_probability)),
        faithful=bool(abs(shap_result.reconstructed_probability[row_index] - raw_rf_probability) <= 1e-4),
        top_positive_contributors=positive,
        top_negative_contributors=negative,
        all_contributors=contributors_sorted_by_magnitude,
    )
