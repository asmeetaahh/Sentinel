"""
The four required models, behind a uniform interface:
    model.fit(X_train, y_train)
    model.predict_score(X) -> np.ndarray of continuous risk scores (higher = riskier)

For B/C/D, predict_score is a genuine calibratable probability
(predict_proba(...)[:, 1]). For A (the historical-threshold baseline), it is
the raw signal value — monotonically related to risk but NOT a probability;
this is documented, not disguised (see HistoricalThresholdBaseline).

Hyperparameters live in config.py, chosen once as sensible defaults and not
tuned against any evaluation result (see the "IMPORTANT ENGINEERING RULE" in
docs/research/baseline_ml_report.md).
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import BASELINE_THRESHOLD_GRID, LOGISTIC_REGRESSION_PARAMS, RANDOM_FOREST_PARAMS, XGBOOST_PARAMS

try:
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
    XGBOOST_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependent
    XGBOOST_AVAILABLE = False
    XGBOOST_IMPORT_ERROR = str(exc)


class HistoricalThresholdBaseline:
    """Model A: a single causal signal (default: chargeback_rate_deviation_z
    — this merchant's own recent chargeback rate vs. its own expanding
    history, see feature_engineering.md) thresholded at a value chosen to
    maximize F1 on the TRAINING split only. No cross-merchant learning
    beyond picking this one global threshold; every input value is already
    computed purely from a single merchant's own past.
    """

    name = "historical_threshold_baseline"
    is_probabilistic = False

    def __init__(self, feature_cols: list[str], signal_feature: str, threshold_grid=None):
        self.feature_cols = feature_cols
        self.signal_feature = signal_feature
        self.signal_idx = feature_cols.index(signal_feature)
        self.threshold_grid = threshold_grid or BASELINE_THRESHOLD_GRID
        self.threshold_ = None
        self._train_min = None
        self._train_max = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "HistoricalThresholdBaseline":
        signal = X[:, self.signal_idx]
        best_f1, best_t = -1.0, self.threshold_grid[0]
        for t in self.threshold_grid:
            preds = (signal >= t).astype(int)
            f1 = f1_score(y, preds, zero_division=0)
            if f1 > best_f1:
                best_f1, best_t = f1, t
        self.threshold_ = best_t
        self._train_min, self._train_max = float(signal.min()), float(signal.max())
        return self

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        return X[:, self.signal_idx]

    def predict_pseudo_probability(self, X: np.ndarray) -> np.ndarray:
        """Min-max scaled (by TRAIN range) version of the signal, in [0,1]
        for plotting only — explicitly NOT a calibrated probability.
        """
        signal = X[:, self.signal_idx]
        span = max(self._train_max - self._train_min, 1e-9)
        return np.clip((signal - self._train_min) / span, 0.0, 1.0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_score(X) >= self.threshold_).astype(int)


class LogisticRegressionModel:
    name = "logistic_regression"
    is_probabilistic = True

    def __init__(self):
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(**LOGISTIC_REGRESSION_PARAMS)),
            ]
        )

    def fit(self, X, y):
        self.pipeline.fit(X, y)
        return self

    def predict_score(self, X) -> np.ndarray:
        return self.pipeline.predict_proba(X)[:, 1]


class RandomForestModel:
    name = "random_forest"
    is_probabilistic = True

    def __init__(self):
        self.model = RandomForestClassifier(**RANDOM_FOREST_PARAMS)

    def fit(self, X, y):
        self.model.fit(X, y)
        return self

    def predict_score(self, X) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def feature_importances(self, feature_cols: list[str]) -> dict:
        return dict(sorted(zip(feature_cols, self.model.feature_importances_.tolist()), key=lambda kv: -kv[1]))


class XGBoostModel:
    name = "xgboost"
    is_probabilistic = True

    def __init__(self):
        if not XGBOOST_AVAILABLE:
            raise RuntimeError(f"xgboost is not usable in this environment: {XGBOOST_IMPORT_ERROR}")
        self.model = None

    def fit(self, X, y):
        n_pos = int(y.sum())
        n_neg = len(y) - n_pos
        scale_pos_weight = n_neg / max(n_pos, 1)  # standard XGBoost imbalance handling, data-driven not tuned
        self.model = XGBClassifier(**XGBOOST_PARAMS, scale_pos_weight=scale_pos_weight)
        self.model.fit(X, y)
        return self

    def predict_score(self, X) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def feature_importances(self, feature_cols: list[str]) -> dict:
        return dict(sorted(zip(feature_cols, self.model.feature_importances_.tolist()), key=lambda kv: -kv[1]))


def build_models(feature_cols: list[str], baseline_signal_feature: str) -> dict:
    models = {
        "historical_threshold_baseline": HistoricalThresholdBaseline(feature_cols, baseline_signal_feature),
        "logistic_regression": LogisticRegressionModel(),
        "random_forest": RandomForestModel(),
    }
    if XGBOOST_AVAILABLE:
        models["xgboost"] = XGBoostModel()
    return models
