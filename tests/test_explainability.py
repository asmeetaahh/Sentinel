"""
Tests for the SHAP explainability layer (ml/explainability).

Covers exactly what the task requires: correct artifact identity (never a
silently-retrained model), feature-column alignment with the artifact's own
recorded order, no forbidden inputs, deterministic explanation generation,
SHAP output shape, positive/negative contribution splitting, feature
manifest metadata mapping, and local-explanation faithfulness within a
tight numerical tolerance (TreeSHAP is exact for tree ensembles, so this is
a precision check, not a loose approximation allowance).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.explainability import artifact as artifact_module
from ml.explainability import global_explanation, leakage, local_explanation, shap_engine
from ml.explainability.config import ARTIFACT_PATH, FAITHFULNESS_ABS_TOLERANCE, HORIZON_DAYS
from ml.explainability.feature_metadata import load_feature_metadata, metadata_for
from ml.modeling import datasets, splits
from ml.modeling.config import SEED

pytestmark = pytest.mark.skipif(
    not ARTIFACT_PATH.exists(),
    reason="model artifact not found — run scripts/evaluate_calibration.py first",
)


@pytest.fixture(scope="module")
def loaded_artifact():
    return artifact_module.load_artifact()


@pytest.fixture(scope="module")
def test_arrays(loaded_artifact):
    tables = datasets.load_raw_tables()
    feature_cols = datasets.load_feature_columns()
    split_df = splits.build_merchant_split(tables["merchants"], seed=SEED)
    frame = datasets.build_horizon_frame(tables, loaded_artifact.horizon_days)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)
    test_frame = frames["normal_test"]
    X_test, y_test = datasets.xy(test_frame, loaded_artifact.feature_columns)
    return {"frame": test_frame, "X": X_test, "y": y_test, "feature_cols": feature_cols}


@pytest.fixture(scope="module")
def shap_result(loaded_artifact, test_arrays):
    explainer = shap_engine.build_explainer(loaded_artifact.base_random_forest)
    return shap_engine.compute_shap_values(explainer, loaded_artifact.base_random_forest, test_arrays["X"][:100])


# ---------------------------------------------------------------------------
# 1. Artifact loading — exact identity, never a silently different model
# ---------------------------------------------------------------------------


def test_artifact_loads_expected_type_and_horizon(loaded_artifact):
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import RandomForestClassifier

    assert isinstance(loaded_artifact.calibrated_pipeline, CalibratedClassifierCV)
    assert isinstance(loaded_artifact.base_random_forest, RandomForestClassifier)
    assert loaded_artifact.horizon_days == HORIZON_DAYS
    assert len(loaded_artifact.feature_columns) == loaded_artifact.base_random_forest.n_features_in_


def test_artifact_load_rejects_wrong_expected_horizon(tmp_path):
    with pytest.raises(ValueError):
        artifact_module.load_artifact(expected_horizon_days=14)


def test_artifact_load_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        artifact_module.load_artifact(artifact_path=tmp_path / "does_not_exist.joblib")


# ---------------------------------------------------------------------------
# 2. Feature-column alignment
# ---------------------------------------------------------------------------


def test_artifact_feature_columns_match_current_feature_manifest(loaded_artifact, test_arrays):
    assert loaded_artifact.feature_columns == test_arrays["feature_cols"]


def test_leakage_check_passes_on_real_feature_columns(loaded_artifact):
    leakage.assert_no_forbidden_columns(loaded_artifact.feature_columns)  # must not raise
    leakage.assert_columns_match_artifact(loaded_artifact.feature_columns, loaded_artifact.feature_columns)  # must not raise


# ---------------------------------------------------------------------------
# 3. No forbidden inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_columns",
    [
        ["gmv_level_28d", "merchant_id"],
        ["gmv_level_28d", "baseline_chargeback_rate"],
        ["gmv_level_28d", "event_type_risk"],
        ["gmv_level_28d", "label_elevated_chargeback"],
        ["gmv_level_28d", "archetype_d2c_fashion"],
        ["gmv_level_28d", "future_chargeback_amount"],
    ],
)
def test_leakage_check_rejects_forbidden_columns(bad_columns):
    with pytest.raises(ValueError):
        leakage.assert_no_forbidden_columns(bad_columns)


def test_leakage_check_rejects_column_order_mismatch(loaded_artifact):
    shuffled = list(reversed(loaded_artifact.feature_columns))
    with pytest.raises(ValueError):
        leakage.assert_columns_match_artifact(shuffled, loaded_artifact.feature_columns)


# ---------------------------------------------------------------------------
# 4/10. SHAP output shape, faithfulness (local explanation consistency)
# ---------------------------------------------------------------------------


def test_shap_output_shape_matches_input(shap_result, test_arrays):
    n_rows = 100
    n_features = len(test_arrays["feature_cols"])
    assert shap_result.shap_values.shape == (n_rows, n_features)
    assert shap_result.raw_probability.shape == (n_rows,)


def test_shap_faithfulness_within_tight_tolerance(shap_result):
    """TreeSHAP is exact for tree ensembles — this must hold to numerical
    precision, not just 'roughly'.
    """
    assert shap_result.faithful
    assert shap_result.max_abs_reconstruction_error <= FAITHFULNESS_ABS_TOLERANCE
    np.testing.assert_allclose(shap_result.reconstructed_probability, shap_result.raw_probability, atol=FAITHFULNESS_ABS_TOLERANCE)


def test_shap_values_are_finite(shap_result):
    assert np.all(np.isfinite(shap_result.shap_values))


# ---------------------------------------------------------------------------
# 5/9. Positive/negative contribution handling
# ---------------------------------------------------------------------------


def test_explain_row_splits_positive_and_negative_correctly(loaded_artifact, test_arrays, shap_result):
    metadata_by_name = load_feature_metadata()
    row_frame = test_arrays["frame"].iloc[0]
    exp = local_explanation.explain_row(
        row_index=0,
        X_row=test_arrays["X"][0],
        shap_result=shap_result,
        feature_columns=loaded_artifact.feature_columns,
        metadata_by_name=metadata_by_name,
        artifact=loaded_artifact,
        calibrated_probability=0.5,
        merchant_id=str(row_frame["merchant_id"]),
        as_of_date=str(row_frame["as_of_date"]),
        day_index=int(row_frame["day_index"]),
    )
    for driver in exp.top_positive_contributors:
        assert driver["shap_value"] > 0
        assert driver["direction"] == "increases_risk"
    for driver in exp.top_negative_contributors:
        assert driver["shap_value"] < 0
        assert driver["direction"] == "decreases_risk"

    # sorted by magnitude, descending
    for a, b in zip(exp.top_positive_contributors, exp.top_positive_contributors[1:]):
        assert a["shap_value"] >= b["shap_value"]
    for a, b in zip(exp.top_negative_contributors, exp.top_negative_contributors[1:]):
        assert a["shap_value"] <= b["shap_value"]


def test_direction_never_inferred_from_feature_name():
    """The sign must come purely from the SHAP value, never from any
    heuristic about the feature's name (e.g. assuming 'chargeback_rate'
    always means risk).
    """
    assert local_explanation._direction(0.01) == "increases_risk"
    assert local_explanation._direction(-0.01) == "decreases_risk"
    assert local_explanation._direction(0.0) == "neutral"


# ---------------------------------------------------------------------------
# 6. Manifest metadata mapping
# ---------------------------------------------------------------------------


def test_manifest_metadata_lookup_for_known_feature():
    metadata_by_name = load_feature_metadata()
    meta = metadata_for("chargeback_rate_28d", metadata_by_name)
    assert meta["group"] == "chargeback_behavior"
    assert "chargeback" in meta["definition"].lower()
    assert meta["window"] is not None


def test_manifest_metadata_lookup_does_not_fabricate_unknown_feature():
    metadata_by_name = load_feature_metadata()
    meta = metadata_for("totally_made_up_feature_xyz", metadata_by_name)
    assert meta["group"] == "unknown"
    assert "not fabricated" in meta["definition"]


def test_all_artifact_features_have_manifest_metadata(loaded_artifact):
    metadata_by_name = load_feature_metadata()
    missing = [f for f in loaded_artifact.feature_columns if f not in metadata_by_name]
    assert missing == [], f"features missing manifest metadata: {missing}"


# ---------------------------------------------------------------------------
# Deterministic explanation generation
# ---------------------------------------------------------------------------


def test_shap_computation_is_deterministic(loaded_artifact, test_arrays):
    explainer1 = shap_engine.build_explainer(loaded_artifact.base_random_forest)
    result1 = shap_engine.compute_shap_values(explainer1, loaded_artifact.base_random_forest, test_arrays["X"][:20])

    explainer2 = shap_engine.build_explainer(loaded_artifact.base_random_forest)
    result2 = shap_engine.compute_shap_values(explainer2, loaded_artifact.base_random_forest, test_arrays["X"][:20])

    np.testing.assert_array_equal(result1.shap_values, result2.shap_values)
    assert result1.base_value == result2.base_value


def test_full_local_explanation_is_deterministic(loaded_artifact, test_arrays, shap_result):
    metadata_by_name = load_feature_metadata()
    row_frame = test_arrays["frame"].iloc[3]
    kwargs = dict(
        row_index=3,
        X_row=test_arrays["X"][3],
        shap_result=shap_result,
        feature_columns=loaded_artifact.feature_columns,
        metadata_by_name=metadata_by_name,
        artifact=loaded_artifact,
        calibrated_probability=0.7,
        merchant_id=str(row_frame["merchant_id"]),
        as_of_date=str(row_frame["as_of_date"]),
        day_index=int(row_frame["day_index"]),
    )
    exp1 = local_explanation.explain_row(**kwargs).to_dict()
    exp2 = local_explanation.explain_row(**kwargs).to_dict()
    assert exp1 == exp2


# ---------------------------------------------------------------------------
# Global explanation
# ---------------------------------------------------------------------------


def test_global_feature_importance_ranking_is_well_formed(loaded_artifact, shap_result):
    metadata_by_name = load_feature_metadata()
    result = global_explanation.global_feature_importance(shap_result, loaded_artifact.feature_columns, metadata_by_name)

    assert len(result["feature_ranking"]) == len(loaded_artifact.feature_columns)
    mean_abs_values = [e["mean_abs_shap"] for e in result["feature_ranking"]]
    assert mean_abs_values == sorted(mean_abs_values, reverse=True)
    assert all(v >= 0 for v in mean_abs_values)

    total_group = sum(e["summed_mean_abs_shap"] for e in result["group_ranking"])
    assert total_group == pytest.approx(sum(mean_abs_values), rel=1e-6)


def test_global_importance_does_not_alter_feature_set(loaded_artifact, shap_result):
    """Global importance is diagnostic only — it must not filter, reorder
    for use as input, or otherwise change what the model actually uses.
    """
    metadata_by_name = load_feature_metadata()
    result = global_explanation.global_feature_importance(shap_result, loaded_artifact.feature_columns, metadata_by_name)
    ranked_features = {e["feature"] for e in result["feature_ranking"]}
    assert ranked_features == set(loaded_artifact.feature_columns)
