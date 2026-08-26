"""
Secondary problem: predict future_chargeback_amount (regression).

Kept deliberately small per the task brief ("do not spend excessive
implementation time on regression if the label structure does not support
a defensible evaluation"). Two models only:
  - naive baseline: the trailing daily chargeback amount, extrapolated
    flat across the horizon (baseline_daily_chargeback_amount_trailing *
    horizon_days) — already computed causally in labels.csv, a standard
    "no change from recent history" forecast.
  - one candidate: RandomForestRegressor on the same 55 causal features,
    trained on log1p(target) because future_chargeback_amount is heavily
    zero-inflated and right-skewed (see docs/research/dataset_validation_report.md).
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import RANDOM_FOREST_PARAMS


def naive_baseline(frame, horizon_days: int) -> np.ndarray:
    return frame["baseline_daily_chargeback_amount_trailing"].to_numpy() * horizon_days


def fit_regression_candidate(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestRegressor:
    params = dict(RANDOM_FOREST_PARAMS)
    params.pop("class_weight", None)
    model = RandomForestRegressor(**params)
    model.fit(X_train, np.log1p(y_train))
    return model


def predict_regression_candidate(model: RandomForestRegressor, X: np.ndarray) -> np.ndarray:
    return np.expm1(model.predict(X))


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mean_true = float(np.mean(y_true))
    normalized_mae_pct = float(100 * mae / mean_true) if mean_true > 0 else None

    return {
        "mae": mae,
        "rmse": rmse,
        "mean_true_value": mean_true,
        "normalized_mae_pct_of_mean": normalized_mae_pct,
        "note_on_percentage_error": (
            "Standard MAPE is not reported: future_chargeback_amount is zero for a large share of rows "
            "(see dataset validation report), making per-row percentage error undefined/unstable. "
            "normalized_mae_pct_of_mean (MAE as a percentage of the mean true value) is reported instead "
            "as a meaningful, stable scale-normalized summary."
        ),
    }
