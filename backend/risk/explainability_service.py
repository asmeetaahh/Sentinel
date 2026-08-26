"""
Exposes the existing verified SHAP explanation pipeline (ml.explainability)
for a single merchant/prediction date. This module does not compute SHAP
values itself — it calls the already-tested ml.explainability functions
with the shared, startup-loaded TreeExplainer (backend/api/state.py).

No LLM, no generated prose, no causal claims — see
docs/architecture/explainability.md.
"""

from __future__ import annotations

from datetime import date

from backend.api.state import AppState
from backend.services.lookups import require_merchant, resolve_day_index
from ml.explainability import shap_engine
from ml.explainability.config import TOP_K_CONTRIBUTORS
from ml.explainability.local_explanation import explain_row


def explain(state: AppState, merchant_id: str, as_of_date: date, top_k: int = TOP_K_CONTRIBUTORS) -> dict:
    require_merchant(state.merchants, merchant_id)
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)

    row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if row.empty:
        raise ValueError(f"No feature row for merchant_id={merchant_id} day_index={day_index}.")
    X_row = row.iloc[0][state.feature_columns].to_numpy(dtype=float).reshape(1, -1)

    artifact = state.artifact
    calibrated_probability = float(artifact.calibrated_pipeline.predict_proba(X_row)[0, 1])

    shap_result = shap_engine.compute_shap_values(state.explainer, artifact.base_random_forest, X_row)
    if not shap_result.faithful:
        raise RuntimeError(
            f"SHAP faithfulness check failed for merchant_id={merchant_id} as_of_date={as_of_date} "
            f"(reconstruction error {shap_result.max_abs_reconstruction_error:.2e}) — refusing to return an explanation."
        )

    explanation = explain_row(
        row_index=0,
        X_row=X_row[0],
        shap_result=shap_result,
        feature_columns=artifact.feature_columns,
        metadata_by_name=state.feature_metadata_by_name,
        artifact=artifact,
        calibrated_probability=calibrated_probability,
        merchant_id=merchant_id,
        as_of_date=as_of_date.isoformat(),
        day_index=day_index,
        top_k=top_k,
    )
    result = explanation.to_dict()
    result["causality_disclaimer"] = (
        "SHAP attributes the model's own output to its inputs. It does not establish that any feature caused "
        "elevated risk, and the model was trained entirely on synthetic data — see docs/architecture/explainability.md."
    )
    return result
