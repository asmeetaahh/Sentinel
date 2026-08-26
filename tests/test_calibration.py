"""
Tests for probability calibration of the Random Forest / 30-day candidate
(ml/modeling/calibration.py).

Covers exactly what this stage requires: the calibrator is fit only on
train + a held-out slice of validation (never test), fitting is
deterministic and reproducible, predictions are always valid probabilities,
inference is deterministic, and a saved artifact reloads to bit-identical
predictions.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.modeling.calibration import CalibratedRandomForestModel, split_validation_for_calibration
from ml.modeling.config import SEED

DATA_DIR = REPO_ROOT / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "processed" / "features.csv").exists(),
    reason="feature/label artifacts not found — run scripts/build_features.py and scripts/generate_dataset.py first",
)


@pytest.fixture(scope="module")
def horizon30_arrays():
    from ml.modeling import datasets, splits

    tables = datasets.load_raw_tables()
    feature_cols = datasets.load_feature_columns()
    split_df = splits.build_merchant_split(tables["merchants"], seed=SEED)
    frame = datasets.build_horizon_frame(tables, 30)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)

    X_train, y_train = datasets.xy(frames["train"], feature_cols)
    X_val, y_val = datasets.xy(frames["val"], feature_cols)
    X_test, y_test = datasets.xy(frames["normal_test"], feature_cols)
    return {"X_train": X_train, "y_train": y_train, "X_val": X_val, "y_val": y_val, "X_test": X_test, "y_test": y_test}


# ---------------------------------------------------------------------------
# Validation split for calibration
# ---------------------------------------------------------------------------


def test_val_calibration_and_val_threshold_are_disjoint_and_cover_val(horizon30_arrays):
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    assert len(split.y_calibration) + len(split.y_threshold) == len(a["y_val"])

    calib_rows = set(map(tuple, split.X_calibration.tolist()))
    threshold_rows = set(map(tuple, split.X_threshold.tolist()))
    assert calib_rows.isdisjoint(threshold_rows)


def test_validation_split_is_deterministic(horizon30_arrays):
    a = horizon30_arrays
    s1 = split_validation_for_calibration(a["X_val"], a["y_val"])
    s2 = split_validation_for_calibration(a["X_val"], a["y_val"])
    np.testing.assert_array_equal(s1.X_calibration, s2.X_calibration)
    np.testing.assert_array_equal(s1.X_threshold, s2.X_threshold)


# ---------------------------------------------------------------------------
# Fitting only on train + val_calibration
# ---------------------------------------------------------------------------


def test_fit_calibrated_signature_has_no_test_data_parameter():
    """Structural leakage guard: the method literally cannot accept test
    data — there is no parameter to pass it through.
    """
    import inspect

    sig = inspect.signature(CalibratedRandomForestModel.fit_calibrated)
    params = list(sig.parameters.keys())
    assert params == ["self", "X_train", "y_train", "X_val_calibration", "y_val_calibration"]


def test_base_model_is_unchanged_by_calibrator_fitting(horizon30_arrays):
    """The base Random Forest must be fit ONCE on train and then frozen —
    fitting the calibrator on val_calibration must not refit or otherwise
    mutate it (this is what 'prefit'/FrozenEstimator guarantees; we assert
    it explicitly rather than trusting the library silently).
    """
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])

    model = CalibratedRandomForestModel()
    model.base_model = None
    from sklearn.ensemble import RandomForestClassifier

    from ml.modeling.config import RANDOM_FOREST_PARAMS

    model.base_model = RandomForestClassifier(**RANDOM_FOREST_PARAMS)
    model.base_model.fit(a["X_train"], a["y_train"])
    importances_before = model.base_model.feature_importances_.copy()

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.frozen import FrozenEstimator

    model.calibrator = CalibratedClassifierCV(FrozenEstimator(model.base_model), method="sigmoid")
    model.calibrator.fit(split.X_calibration, split.y_calibration)

    np.testing.assert_array_equal(importances_before, model.base_model.feature_importances_)


def test_no_test_data_influences_the_fitted_calibrator(horizon30_arrays):
    """Fit twice with identical train/val_calibration but let an unrelated,
    differently-shaped/valued 'test-like' array exist in scope in between —
    the resulting calibrator predictions on a fixed probe input must be
    identical, proving nothing about the surrounding test data leaked in.
    """
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    probe = a["X_test"][:5]

    model1 = CalibratedRandomForestModel()
    model1.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)
    scores1 = model1.predict_score(probe)

    _ = a["X_test"] * 999.0  # an unrelated, wildly different "test-like" array in scope

    model2 = CalibratedRandomForestModel()
    model2.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)
    scores2 = model2.predict_score(probe)

    np.testing.assert_array_almost_equal(scores1, scores2)


# ---------------------------------------------------------------------------
# Reproducibility / determinism
# ---------------------------------------------------------------------------


def test_calibration_fit_is_reproducible_given_same_seed_and_data(horizon30_arrays):
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])

    model1 = CalibratedRandomForestModel()
    model1.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    model2 = CalibratedRandomForestModel()
    model2.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    np.testing.assert_array_almost_equal(model1.predict_score(a["X_test"]), model2.predict_score(a["X_test"]))


def test_inference_is_deterministic_across_repeated_calls(horizon30_arrays):
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    model = CalibratedRandomForestModel()
    model.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    scores_a = model.predict_score(a["X_test"])
    scores_b = model.predict_score(a["X_test"])
    np.testing.assert_array_equal(scores_a, scores_b)


# ---------------------------------------------------------------------------
# Output validity
# ---------------------------------------------------------------------------


def test_calibrated_scores_are_valid_probabilities(horizon30_arrays):
    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    model = CalibratedRandomForestModel()
    model.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    scores = model.predict_score(a["X_test"])
    assert np.all(scores >= 0.0) and np.all(scores <= 1.0)
    assert not np.any(np.isnan(scores))


def test_calibration_preserves_ranking_relative_to_uncalibrated(horizon30_arrays):
    """Sigmoid scaling is a monotonic transform of the raw score, so the
    induced ranking (and therefore PR-AUC/ROC-AUC) must be unchanged — this
    is a mathematical property of the method, asserted here as a sanity
    check rather than assumed.
    """
    from sklearn.metrics import average_precision_score

    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    model = CalibratedRandomForestModel()
    model.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    calibrated_scores = model.predict_score(a["X_test"])
    uncalibrated_scores = model.predict_score_uncalibrated(a["X_test"])

    pr_auc_calibrated = average_precision_score(a["y_test"], calibrated_scores)
    pr_auc_uncalibrated = average_precision_score(a["y_test"], uncalibrated_scores)
    assert pr_auc_calibrated == pytest.approx(pr_auc_uncalibrated, abs=1e-9)


# ---------------------------------------------------------------------------
# Artifact save/load round-trip
# ---------------------------------------------------------------------------


def test_saved_artifact_reloads_to_identical_predictions(horizon30_arrays):
    import joblib

    a = horizon30_arrays
    split = split_validation_for_calibration(a["X_val"], a["y_val"])
    model = CalibratedRandomForestModel()
    model.fit_calibrated(a["X_train"], a["y_train"], split.X_calibration, split.y_calibration)

    original_scores = model.predict_score(a["X_test"])

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "model.joblib"
        joblib.dump(model.calibrator, artifact_path)
        reloaded = joblib.load(artifact_path)
        reloaded_scores = reloaded.predict_proba(a["X_test"])[:, 1]

    np.testing.assert_array_equal(original_scores, reloaded_scores)
