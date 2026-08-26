"""
Causal feature-engineering pipeline: daily_observations -> merchant-level
features, one row per (merchant_id, day_index=t), using only information
available at or before t.

Structural leakage guarantees (see docs/architecture/feature_engineering.md
for the full writeup):
  - This module never imports/reads data/scenarios/events.csv or
    data/processed/labels.csv. There is no code path by which scenario
    identity or label information could enter the feature matrix.
  - From merchants.csv, only `merchant_id` and `signup_date` are read —
    never any `baseline_*` column (those are generator ground-truth
    parameters, not observable to a real system; see the leakage audit in
    docs/research/dataset_validation_report.md).
  - Every per-row value is produced by a trailing window ending at t
    (inclusive) or an expanding window over day_index <= t. No centered,
    forward, or whole-series statistic is used anywhere.

Feature groups (see FEATURE_MANIFEST for the authoritative per-feature
list): payment behavior, refund behavior, chargeback behavior, fulfillment,
customer mix, financial state, merchant behavior, temporal
velocity/acceleration, deviation from merchant-specific baseline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    DEVIATION_METRICS,
    PAYMENT_METHODS,
    RECENCY_CAP_DAYS,
    VELOCITY_RATE_METRICS,
    WINDOW_LONG,
    WINDOW_MEDIUM,
    WINDOW_SHORT,
)
from .primitives import (
    deviation_zscore,
    days_since_last_positive,
    hhi,
    l1_drift,
    payment_mix_weighted_shares,
    rolling_mean,
    rolling_std,
    rolling_sum,
    rolling_volume_weighted_rate,
    rolling_weighted_mean,
    velocity_diff,
    velocity_ratio,
)

CAUSAL_OK = "causal (uses only merchant_id, day_index<=t) — safe"

# Populated by build_features(); each entry:
#   name, group, definition, source_columns, window, kind, leakage_status
FEATURE_MANIFEST: list[dict] = []


def _record(name, group, definition, source_columns, window, kind):
    FEATURE_MANIFEST.append(
        {
            "name": name,
            "group": group,
            "definition": definition,
            "source_columns": source_columns,
            "window": window,
            "kind": kind,
            "leakage_status": CAUSAL_OK,
        }
    )


def load_inputs(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = Path(data_dir)
    daily = pd.read_csv(data_dir / "raw" / "daily_observations.csv", parse_dates=["date"])
    merchants = pd.read_csv(data_dir / "raw" / "merchants.csv", parse_dates=["signup_date"])
    # Structural guarantee: only these two columns are ever taken from
    # merchants.csv. Every baseline_* ground-truth column is dropped here,
    # at the point of entry, so it cannot accidentally flow downstream.
    merchants = merchants[["merchant_id", "signup_date"]]
    return daily, merchants


def build_features(daily: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    FEATURE_MANIFEST.clear()

    df = daily.sort_values(["merchant_id", "day_index"]).reset_index(drop=True)
    out = df[["merchant_id", "date", "day_index"]].copy()

    W = {WINDOW_SHORT: "7d", WINDOW_MEDIUM: "28d", WINDOW_LONG: "60d"}

    # -----------------------------------------------------------------
    # Group 1: Payment behavior — mix concentration + drift.
    # -----------------------------------------------------------------
    shares = {w: payment_mix_weighted_shares(df, PAYMENT_METHODS, w) for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG)}
    for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG):
        name = f"payment_mix_hhi_{W[w]}"
        out[name] = hhi(shares[w])
        _record(
            name, "payment_behavior",
            f"Herfindahl-Hirschman index (sum of squared GMV-weighted payment-method shares) over trailing {W[w]}. Higher = more concentrated in one method.",
            [f"pct_pay_{m}" for m in PAYMENT_METHODS] + ["gmv"], W[w], "level",
        )

    out["payment_mix_l1_drift_7v28"] = l1_drift(shares[WINDOW_SHORT], shares[WINDOW_MEDIUM])
    _record(
        "payment_mix_l1_drift_7v28", "payment_behavior",
        "Sum of |share_i(7d) - share_i(28d)| across payment methods — how much the mix has moved recently vs. the medium-term.",
        [f"pct_pay_{m}" for m in PAYMENT_METHODS] + ["gmv"], "7d vs 28d", "ratio",
    )
    out["payment_mix_l1_drift_28v60"] = l1_drift(shares[WINDOW_MEDIUM], shares[WINDOW_LONG])
    _record(
        "payment_mix_l1_drift_28v60", "payment_behavior",
        "Sum of |share_i(28d) - share_i(60d)| across payment methods — medium-term vs. long-term mix drift.",
        [f"pct_pay_{m}" for m in PAYMENT_METHODS] + ["gmv"], "28d vs 60d", "ratio",
    )

    # -----------------------------------------------------------------
    # Group 2: Refund behavior.
    # -----------------------------------------------------------------
    refund_rate_by_w = {}
    for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG):
        name = f"refund_rate_{W[w]}"
        s = rolling_volume_weighted_rate(df, "refund_count", "transaction_count", w)
        out[name] = s
        refund_rate_by_w[w] = s
        _record(
            name, "refund_behavior",
            f"Volume-weighted refund rate over trailing {W[w]}: sum(refund_count)/sum(transaction_count). Not a mean of daily rates, to avoid low-count distortion.",
            ["refund_count", "transaction_count"], W[w], "level",
        )

    out["refund_amount_to_gmv_28d"] = rolling_volume_weighted_rate(df, "refund_amount", "gmv", WINDOW_MEDIUM)
    _record(
        "refund_amount_to_gmv_28d", "refund_behavior",
        "Dollar-weighted refund burden: sum(refund_amount)/sum(gmv) over trailing 28d.",
        ["refund_amount", "gmv"], "28d", "ratio",
    )
    out["refund_count_28d"] = rolling_sum(df, "refund_count", WINDOW_MEDIUM)
    _record(
        "refund_count_28d", "refund_behavior",
        "Raw refund count over trailing 28d — exposure/confidence context for refund_rate_28d (a rate from 2 refunds is far less reliable than one from 50).",
        ["refund_count"], "28d", "level",
    )

    # -----------------------------------------------------------------
    # Group 3: Chargeback behavior.
    # -----------------------------------------------------------------
    chargeback_rate_by_w = {}
    for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG):
        name = f"chargeback_rate_{W[w]}"
        s = rolling_volume_weighted_rate(df, "chargeback_count", "transaction_count", w)
        out[name] = s
        chargeback_rate_by_w[w] = s
        _record(
            name, "chargeback_behavior",
            f"Volume-weighted chargeback rate over trailing {W[w]}: sum(chargeback_count)/sum(transaction_count).",
            ["chargeback_count", "transaction_count"], W[w], "level",
        )

    out["chargeback_amount_to_gmv_28d"] = rolling_volume_weighted_rate(df, "chargeback_amount", "gmv", WINDOW_MEDIUM)
    _record(
        "chargeback_amount_to_gmv_28d", "chargeback_behavior",
        "Dollar-weighted chargeback exposure: sum(chargeback_amount)/sum(gmv) over trailing 28d.",
        ["chargeback_amount", "gmv"], "28d", "ratio",
    )
    out["chargeback_count_28d"] = rolling_sum(df, "chargeback_count", WINDOW_MEDIUM)
    _record(
        "chargeback_count_28d", "chargeback_behavior",
        "Raw chargeback count over trailing 28d — exposure/confidence context for chargeback_rate_28d.",
        ["chargeback_count"], "28d", "level",
    )
    out["days_since_last_chargeback"] = days_since_last_positive(df, "chargeback_count", cap=RECENCY_CAP_DAYS)
    _record(
        "days_since_last_chargeback", "chargeback_behavior",
        f"Days since the most recent day (<=t) with chargeback_count>0 for this merchant, capped at {RECENCY_CAP_DAYS}. A recency signal that doesn't collapse to 0 on days with no observed chargebacks yet.",
        ["chargeback_count", "day_index"], "expanding (capped)", "level",
    )

    # -----------------------------------------------------------------
    # Group 4: Fulfillment.
    # -----------------------------------------------------------------
    fulfillment_on_time_by_w = {}
    for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG):
        name = f"fulfillment_on_time_rate_{W[w]}"
        s = rolling_weighted_mean(df, "fulfillment_on_time_rate", "transaction_count", w)
        out[name] = s
        fulfillment_on_time_by_w[w] = s
        _record(
            name, "fulfillment",
            f"Transaction-volume-weighted mean of fulfillment_on_time_rate over trailing {W[w]}.",
            ["fulfillment_on_time_rate", "transaction_count"], W[w], "level",
        )
    out["fulfillment_delay_avg_days_28d"] = rolling_weighted_mean(df, "fulfillment_delay_avg_days", "transaction_count", WINDOW_MEDIUM)
    _record(
        "fulfillment_delay_avg_days_28d", "fulfillment",
        "Transaction-volume-weighted mean fulfillment delay (days) over trailing 28d.",
        ["fulfillment_delay_avg_days", "transaction_count"], "28d", "level",
    )

    # -----------------------------------------------------------------
    # Group 5: Customer mix.
    # -----------------------------------------------------------------
    new_customer_rate_by_w = {}
    for w in (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG):
        name = f"new_customer_rate_{W[w]}"
        s = rolling_volume_weighted_rate(df, "new_customers", "customer_count", w)
        out[name] = s
        new_customer_rate_by_w[w] = s
        _record(
            name, "customer_mix",
            f"Volume-weighted new-customer share over trailing {W[w]}: sum(new_customers)/sum(customer_count).",
            ["new_customers", "customer_count"], W[w], "level",
        )
    out["customer_count_28d"] = rolling_mean(df, "customer_count", WINDOW_MEDIUM)
    _record(
        "customer_count_28d", "customer_mix",
        "Mean daily distinct customer count over trailing 28d — activity scale context.",
        ["customer_count"], "28d", "level",
    )

    # -----------------------------------------------------------------
    # Group 6: Financial state (liquidity/settlement) — kept as
    # interpretable levels/ratios, not a derived "risk score".
    # -----------------------------------------------------------------
    out["liquidity_balance_28d"] = rolling_mean(df, "liquidity_balance", WINDOW_MEDIUM)
    _record(
        "liquidity_balance_28d", "financial_state",
        "Mean daily liquidity_balance over trailing 28d (same units as gmv).",
        ["liquidity_balance"], "28d", "level",
    )
    gmv_28d_mean = rolling_mean(df, "gmv", WINDOW_MEDIUM)
    out["liquidity_to_gmv_ratio_28d"] = out["liquidity_balance_28d"] / gmv_28d_mean.clip(lower=1.0)
    _record(
        "liquidity_to_gmv_ratio_28d", "financial_state",
        "liquidity_balance_28d / mean(gmv, 28d) — buffer expressed as 'days of current GMV', directly interpretable.",
        ["liquidity_balance", "gmv"], "28d", "ratio",
    )
    pending_28d_mean = rolling_mean(df, "pending_settlement_amount", WINDOW_MEDIUM)
    out["pending_settlement_to_gmv_28d"] = pending_28d_mean / gmv_28d_mean.clip(lower=1.0)
    _record(
        "pending_settlement_to_gmv_28d", "financial_state",
        "mean(pending_settlement_amount, 28d) / mean(gmv, 28d) — settlement pipeline scale relative to volume.",
        ["pending_settlement_amount", "gmv"], "28d", "ratio",
    )
    liquidity_std_28d = rolling_std(df, "liquidity_balance", WINDOW_MEDIUM)
    out["liquidity_coefficient_of_variation_28d"] = liquidity_std_28d / out["liquidity_balance_28d"].clip(lower=1.0)
    _record(
        "liquidity_coefficient_of_variation_28d", "financial_state",
        "std(liquidity_balance, 28d) / mean(liquidity_balance, 28d) — how stable the buffer has been recently.",
        ["liquidity_balance"], "28d", "ratio",
    )

    # -----------------------------------------------------------------
    # Group 7: Merchant behavior — scale, tenure, calendar context.
    # -----------------------------------------------------------------
    out["gmv_level_28d"] = gmv_28d_mean
    _record("gmv_level_28d", "merchant_behavior", "Mean daily gmv over trailing 28d.", ["gmv"], "28d", "level")

    txn_28d_mean = rolling_mean(df, "transaction_count", WINDOW_MEDIUM)
    out["transaction_count_level_28d"] = txn_28d_mean
    _record("transaction_count_level_28d", "merchant_behavior", "Mean daily transaction_count over trailing 28d.", ["transaction_count"], "28d", "level")

    gmv_std_28d = rolling_std(df, "gmv", WINDOW_MEDIUM)
    out["gmv_coefficient_of_variation_28d"] = gmv_std_28d / gmv_28d_mean.clip(lower=1.0)
    _record(
        "gmv_coefficient_of_variation_28d", "merchant_behavior",
        "std(gmv, 28d) / mean(gmv, 28d) — the merchant's own day-to-day noisiness, context for interpreting other deviations.",
        ["gmv"], "28d", "ratio",
    )

    merged_signup = df[["merchant_id", "date"]].merge(merchants, on="merchant_id", how="left")
    out["merchant_tenure_days"] = (merged_signup["date"] - merged_signup["signup_date"]).dt.days
    _record(
        "merchant_tenure_days", "merchant_behavior",
        "date - signup_date, in days. A real business-facing attribute (account age), not a generator ground-truth risk parameter — the only merchants.csv-derived feature in this pipeline.",
        ["date (daily_observations)", "signup_date (merchants)"], "n/a (point-in-time)", "level",
    )

    dow = df["date"].dt.dayofweek
    out["is_weekend"] = (dow >= 5).astype(int)
    _record("is_weekend", "merchant_behavior", "1 if the observation date is Saturday/Sunday, else 0.", ["date"], "n/a (point-in-time)", "level")

    doy = df["date"].dt.dayofyear.astype(float)
    out["day_of_year_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["day_of_year_cos"] = np.cos(2 * np.pi * doy / 365.25)
    _record("day_of_year_sin", "merchant_behavior", "sin(2*pi*day_of_year/365.25) — cyclical calendar position, lets a model account for seasonality explicitly.", ["date"], "n/a (point-in-time)", "level")
    _record("day_of_year_cos", "merchant_behavior", "cos(2*pi*day_of_year/365.25) — paired with day_of_year_sin for a non-discontinuous yearly cycle encoding.", ["date"], "n/a (point-in-time)", "level")

    # -----------------------------------------------------------------
    # Group 8: Temporal velocity / acceleration (dedicated).
    # -----------------------------------------------------------------
    rate_series_by_metric = {
        "chargeback_rate": chargeback_rate_by_w,
        "refund_rate": refund_rate_by_w,
        "fulfillment_on_time_rate": fulfillment_on_time_by_w,
    }
    rate_source_columns = {
        "chargeback_rate": ["chargeback_count", "transaction_count"],
        "refund_rate": ["refund_count", "transaction_count"],
        "fulfillment_on_time_rate": ["fulfillment_on_time_rate", "transaction_count"],
    }
    for metric in VELOCITY_RATE_METRICS:
        s = rate_series_by_metric[metric]
        src = rate_source_columns[metric]
        vel_short = velocity_diff(s[WINDOW_SHORT], s[WINDOW_MEDIUM])
        vel_long = velocity_diff(s[WINDOW_MEDIUM], s[WINDOW_LONG])
        out[f"{metric}_velocity_7v28"] = vel_short
        _record(f"{metric}_velocity_7v28", "temporal_velocity", f"{metric}(7d) - {metric}(28d) — short-term momentum (percentage points).", src, "7d vs 28d", "velocity")
        out[f"{metric}_velocity_28v60"] = vel_long
        _record(f"{metric}_velocity_28v60", "temporal_velocity", f"{metric}(28d) - {metric}(60d) — medium-term momentum (percentage points).", src, "28d vs 60d", "velocity")
        out[f"{metric}_acceleration"] = vel_short - vel_long
        _record(f"{metric}_acceleration", "temporal_velocity", "velocity_7v28 - velocity_28v60 — is short-term momentum itself increasing (acceleration) or fading?", src, "7d/28d/60d composite", "acceleration")

    gmv_vel_short = velocity_ratio(rolling_mean(df, "gmv", WINDOW_SHORT), gmv_28d_mean)
    gmv_vel_long = velocity_ratio(gmv_28d_mean, rolling_mean(df, "gmv", WINDOW_LONG))
    out["gmv_velocity_7v28"] = gmv_vel_short
    _record("gmv_velocity_7v28", "temporal_velocity", "mean(gmv,7d)/mean(gmv,28d) - 1 — relative GMV growth, short vs medium term.", ["gmv"], "7d vs 28d", "velocity")
    out["gmv_velocity_28v60"] = gmv_vel_long
    _record("gmv_velocity_28v60", "temporal_velocity", "mean(gmv,28d)/mean(gmv,60d) - 1 — relative GMV growth, medium vs long term.", ["gmv"], "28d vs 60d", "velocity")
    out["gmv_acceleration"] = gmv_vel_short - gmv_vel_long
    _record("gmv_acceleration", "temporal_velocity", "gmv_velocity_7v28 - gmv_velocity_28v60 — is GMV growth speeding up or slowing down?", ["gmv"], "7d/28d/60d composite", "acceleration")

    out["transaction_count_velocity_7v28"] = velocity_ratio(rolling_mean(df, "transaction_count", WINDOW_SHORT), txn_28d_mean)
    _record("transaction_count_velocity_7v28", "temporal_velocity", "mean(transaction_count,7d)/mean(transaction_count,28d) - 1.", ["transaction_count"], "7d vs 28d", "velocity")

    out["new_customer_rate_velocity_7v28"] = velocity_diff(new_customer_rate_by_w[WINDOW_SHORT], new_customer_rate_by_w[WINDOW_MEDIUM])
    _record("new_customer_rate_velocity_7v28", "temporal_velocity", "new_customer_rate(7d) - new_customer_rate(28d).", ["new_customers", "customer_count"], "7d vs 28d", "velocity")

    # -----------------------------------------------------------------
    # Group 9: Deviation from merchant-specific baseline.
    #
    # "Baseline" = this merchant's OWN expanding (day 0..t) mean/std of its
    # 28d-rolling series for the metric (smoothed, to avoid the baseline
    # itself being noise-dominated by single low-count days). "Current" =
    # the 7d-rolling value. This is causal: the expanding window only ever
    # includes day_index <= t.
    # -----------------------------------------------------------------
    deviation_current = {
        "chargeback_rate": chargeback_rate_by_w[WINDOW_SHORT],
        "refund_rate": refund_rate_by_w[WINDOW_SHORT],
        "gmv": rolling_mean(df, "gmv", WINDOW_SHORT),
        "fulfillment_on_time_rate": fulfillment_on_time_by_w[WINDOW_SHORT],
        "new_customer_rate": new_customer_rate_by_w[WINDOW_SHORT],
    }
    deviation_baseline_series = {
        "chargeback_rate": chargeback_rate_by_w[WINDOW_MEDIUM],
        "refund_rate": refund_rate_by_w[WINDOW_MEDIUM],
        "gmv": gmv_28d_mean,
        "fulfillment_on_time_rate": fulfillment_on_time_by_w[WINDOW_MEDIUM],
        "new_customer_rate": new_customer_rate_by_w[WINDOW_MEDIUM],
    }
    for metric in DEVIATION_METRICS:
        name = f"{metric}_deviation_z"
        out[name] = deviation_zscore(df, deviation_current[metric], deviation_baseline_series[metric])
        _record(
            name, "deviation_from_baseline",
            f"(current 7d {metric} - this merchant's own expanding-history mean of its 28d {metric}) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history.",
            [metric], "7d vs expanding(28d-smoothed)", "deviation",
        )

    out["liquidity_deviation_z"] = deviation_zscore(df, rolling_mean(df, "liquidity_balance", WINDOW_SHORT), out["liquidity_balance_28d"])
    _record(
        "liquidity_deviation_z", "deviation_from_baseline",
        "(current 7d liquidity_balance - this merchant's own expanding-history mean of its 28d liquidity_balance) / expanding std, clipped to [-10,10].",
        ["liquidity_balance"], "7d vs expanding(28d-smoothed)", "deviation",
    )

    return out


def build_feature_manifest_df() -> pd.DataFrame:
    return pd.DataFrame(FEATURE_MANIFEST)


def feature_columns(features_df: pd.DataFrame) -> list[str]:
    key_cols = {"merchant_id", "date", "day_index"}
    return [c for c in features_df.columns if c not in key_cols]
