"""
Exposure estimate and liquidity-stress derivation.

Per PROJECT_CONTEXT.md:
    liquidity_stress = predicted_chargeback_exposure / available_merchant_liquidity
This is a DERIVED business metric, computed transparently — it is NOT an
ML prediction.

Exposure status (see docs/research/baseline_ml_report.md §I): the
Random Forest regression candidate evaluated in research did not
outperform a simple trailing-average baseline and was never saved as a
product artifact. Rather than invent a "model" number that doesn't exist,
this service exposes the same deterministic, trailing-average
extrapolation used as the regression baseline in research — clearly
labeled as a non-ML derivation, not a model prediction — alongside the
retrospective actual outcome where the synthetic benchmark's fixed future
happens to make one available (never available in a live deployment;
included for research/debugging transparency only).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from backend.api.state import AppState

TRAILING_WINDOW_DAYS = 28  # matches ml/data_generation/labels.py's own trailing baseline window


def _trailing_daily_chargeback_amount(daily_observations: pd.DataFrame, merchant_id: str, day_index: int) -> float:
    merchant_daily = daily_observations[
        (daily_observations["merchant_id"] == merchant_id) & (daily_observations["day_index"] <= day_index)
    ].sort_values("day_index")
    trailing = merchant_daily.tail(TRAILING_WINDOW_DAYS)
    return float(trailing["chargeback_amount"].mean())


def naive_exposure_estimate(state: AppState, merchant_id: str, day_index: int, horizon_days: int) -> dict:
    trailing_daily = _trailing_daily_chargeback_amount(state.daily_observations, merchant_id, day_index)
    estimate = trailing_daily * horizon_days
    return {
        "value": estimate,
        "provenance": "derived",
        "method": f"trailing {TRAILING_WINDOW_DAYS}-day mean daily chargeback_amount extrapolated flat across the {horizon_days}-day horizon",
        "note": (
            "Deterministic extrapolation from observed data, not an ML prediction. A Random Forest regression "
            "candidate was evaluated in research but did not outperform this baseline at this horizon and is not "
            "exposed as a product prediction — see docs/research/baseline_ml_report.md section I."
        ),
    }


def retrospective_actual_exposure(state: AppState, merchant_id: str, as_of_date: date, horizon_days: int) -> dict:
    match = state.labels[
        (state.labels["merchant_id"] == merchant_id)
        & (state.labels["as_of_date"].dt.date == as_of_date)
        & (state.labels["horizon_days"] == horizon_days)
    ]
    if match.empty:
        return {
            "value": None,
            "available": False,
            "provenance": "observed",
            "note": (
                "Not available: this prediction date's future window extends beyond the synthetic benchmark's "
                "generated history (or the benchmark data does not cover it). In a live deployment this would "
                "never be available at prediction time regardless."
            ),
        }
    row = match.iloc[0]
    return {
        "value": float(row["future_chargeback_amount"]),
        "available": True,
        "provenance": "observed",
        "note": (
            "Only available because this synthetic benchmark's future is already generated and fixed. "
            "A live deployment would never have this at prediction time — included here for research/debugging "
            "comparison against the exposure estimate above, not as a product feature."
        ),
    }


def available_liquidity(state: AppState, merchant_id: str, day_index: int) -> dict:
    row = state.daily_observations[
        (state.daily_observations["merchant_id"] == merchant_id) & (state.daily_observations["day_index"] == day_index)
    ].iloc[0]
    return {
        "value": float(row["liquidity_balance"]),
        "provenance": "observed",
        "note": "Same-day liquidity_balance from daily observations — a simplified, synthetic mean-reverting proxy, not a real settlement ledger (see docs/architecture/data_generation.md limitations).",
    }


def liquidity_stress(exposure_value: float | None, liquidity_value: float) -> dict:
    if exposure_value is None:
        return {"value": None, "provenance": "derived", "note": "Not computed: no exposure estimate available."}
    if liquidity_value <= 0:
        return {"value": None, "provenance": "derived", "note": "Not computed: available liquidity is zero or negative."}
    return {
        "value": exposure_value / liquidity_value,
        "provenance": "derived",
        "formula": "predicted_chargeback_exposure / available_merchant_liquidity",
        "note": "Transparent derived ratio, not an ML prediction, per PROJECT_CONTEXT.md.",
    }
