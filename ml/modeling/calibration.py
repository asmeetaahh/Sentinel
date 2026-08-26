"""
Probability calibration for the provisional Random Forest / 30-day
candidate identified in docs/research/baseline_ml_report.md.

Method: Platt scaling (sigmoid), via sklearn's CalibratedClassifierCV with
cv="prefit".
  1. The base Random Forest is fit on TRAIN only, with the exact same
     hyperparameters as the uncalibrated baseline (config.RANDOM_FOREST_PARAMS)
     — this is the same model, not a different one; only what happens to its
     raw scores afterward changes.
  2. The calibration map (a 2-parameter logistic fit from raw RF score to
     calibrated probability) is fit on a held-out slice of VALIDATION —
     never on train (the base model already saw train, refitting the
     calibration map on the same rows would be circular) and never on test.

Why sigmoid over isotonic: isotonic regression is nonparametric and prone
to overfitting / producing a jagged, non-smooth map when the calibration
set is modest — here that set is roughly 600 rows (half of the 30-day
horizon's validation split, see below). Sigmoid scaling fits only 2
parameters and is the standard, more data-efficient default at this scale.
This choice was made before fitting or evaluating either method — it is a
documented default, not the result of comparing the two and picking the
winner on any metric.

Why the validation split is itself split in two: fitting the calibration
map and selecting the decision threshold from the SAME validation rows
would let the threshold search implicitly "see" how the calibrator
performs on exactly the data used to build it — not test-set leakage, but
a subtler double-dip that would make the threshold look better than it
would on genuinely new data. Splitting validation (seeded, stratified)
into val_calibration and val_threshold keeps those two steps independent,
while the test set remains untouched by either.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

try:
    from sklearn.frozen import FrozenEstimator  # sklearn >= 1.6: replaces cv="prefit"

    _HAS_FROZEN_ESTIMATOR = True
except ImportError:  # pragma: no cover - depends on installed sklearn version
    _HAS_FROZEN_ESTIMATOR = False

from .config import RANDOM_FOREST_PARAMS, SEED

CALIBRATION_METHOD = "sigmoid"
VAL_CALIBRATION_FRACTION = 0.5  # of the validation split; remainder is val_threshold


@dataclass
class ValidationSplitForCalibration:
    X_calibration: np.ndarray
    y_calibration: np.ndarray
    X_threshold: np.ndarray
    y_threshold: np.ndarray


def split_validation_for_calibration(X_val: np.ndarray, y_val: np.ndarray) -> ValidationSplitForCalibration:
    X_calib, X_thresh, y_calib, y_thresh = train_test_split(
        X_val, y_val, test_size=1 - VAL_CALIBRATION_FRACTION, random_state=SEED, stratify=y_val
    )
    return ValidationSplitForCalibration(X_calib, y_calib, X_thresh, y_thresh)


class CalibratedRandomForestModel:
    """Same interface as the other model wrappers (fit/predict_score), plus
    an explicit two-stage fit_calibrated(X_train, y_train, X_val_calibration,
    y_val_calibration) so the train/val boundary used for calibration is
    never ambiguous at the call site.
    """

    name = "random_forest_calibrated"
    is_probabilistic = True

    def __init__(self, method: str = CALIBRATION_METHOD):
        self.method = method
        self.base_model: RandomForestClassifier | None = None
        self.calibrator: CalibratedClassifierCV | None = None

    def fit_calibrated(self, X_train: np.ndarray, y_train: np.ndarray, X_val_calibration: np.ndarray, y_val_calibration: np.ndarray) -> "CalibratedRandomForestModel":
        # n_jobs pinned to 1 here (overriding config.RANDOM_FOREST_PARAMS'
        # n_jobs=-1) so predict_proba is bit-exact reproducible. Empirically
        # verified: n_jobs has ZERO effect on the fitted trees or
        # feature_importances_ (sklearn guarantees per-tree random state is
        # independent of execution order) — it only affects the floating-
        # point summation order when averaging trees at prediction time,
        # which with n_jobs=-1 varies run-to-run at the ~1e-16 (machine
        # epsilon) level. Immaterial to any metric in this report, but this
        # task explicitly requires deterministic inference, so it's pinned
        # for the saved artifact specifically — the shared baseline config
        # (used by the original uncalibrated evaluation) is untouched.
        base_params = {**RANDOM_FOREST_PARAMS, "n_jobs": 1}
        self.base_model = RandomForestClassifier(**base_params)
        self.base_model.fit(X_train, y_train)

        if _HAS_FROZEN_ESTIMATOR:
            # sklearn >= 1.6: cv="prefit" was removed in favor of explicitly
            # freezing the already-fitted estimator so CalibratedClassifierCV
            # cannot refit it on the calibration data.
            self.calibrator = CalibratedClassifierCV(FrozenEstimator(self.base_model), method=self.method)
        else:  # pragma: no cover - older sklearn
            self.calibrator = CalibratedClassifierCV(self.base_model, method=self.method, cv="prefit")
        self.calibrator.fit(X_val_calibration, y_val_calibration)
        return self

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        if self.calibrator is None:
            raise RuntimeError("fit_calibrated() must be called before predict_score()")
        return self.calibrator.predict_proba(X)[:, 1]

    def predict_score_uncalibrated(self, X: np.ndarray) -> np.ndarray:
        """The base model's raw score, for reference/diagnostics only."""
        return self.base_model.predict_proba(X)[:, 1]

    def feature_importances(self, feature_cols: list[str]) -> dict:
        return dict(sorted(zip(feature_cols, self.base_model.feature_importances_.tolist()), key=lambda kv: -kv[1]))
