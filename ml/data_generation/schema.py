"""
Machine-readable schema for the four output tables.

Each entry is (column_name, dtype_str, description). dtype_str values are
pandas/numpy dtype names. This module is the single source of truth used by:
  - generator.py (column ordering when assembling DataFrames)
  - io_utils.py (writing data/metadata/schema.json)
  - tests (column presence / dtype sanity checks)
  - docs/data_generation.md (kept in sync manually with this file)
"""

from __future__ import annotations

MERCHANTS_SCHEMA = [
    ("merchant_id", "string", "Stable synthetic merchant identifier, e.g. M0001."),
    ("archetype", "string", "One of the 8 fixed merchant archetypes."),
    ("business_tier", "string", "small | mid | large — drives baseline GMV scale."),
    ("signup_date", "date", "Synthetic platform signup date, always before the observation window start."),
    ("baseline_daily_gmv", "float64", "Merchant-specific mean daily GMV before trend/seasonality/events/noise."),
    ("baseline_daily_txn_count", "float64", "Merchant-specific mean daily transaction count."),
    ("baseline_aov", "float64", "Merchant-specific baseline average order value."),
    ("baseline_refund_rate", "float64", "Baseline fraction of transactions refunded."),
    ("baseline_chargeback_rate", "float64", "Baseline fraction of transactions charged back."),
    ("baseline_fulfillment_delay_days", "float64", "Baseline average fulfillment delay in days."),
    ("baseline_on_time_rate", "float64", "Baseline fraction of orders fulfilled on time."),
    ("baseline_new_customer_rate", "float64", "Baseline fraction of daily customers who are new."),
    ("baseline_pct_pay_card", "float64", "Baseline card payment share."),
    ("baseline_pct_pay_upi", "float64", "Baseline UPI payment share."),
    ("baseline_pct_pay_netbanking", "float64", "Baseline netbanking payment share."),
    ("baseline_pct_pay_wallet", "float64", "Baseline wallet payment share."),
    ("baseline_pct_pay_bnpl", "float64", "Baseline BNPL payment share."),
    ("annual_growth_rate", "float64", "Organic annualized growth drift applied to baseline GMV/txn, independent of events."),
    ("volatility_factor", "float64", "Day-to-day multiplicative noise std applied to GMV/txn."),
    ("liquidity_buffer_days", "float64", "Target liquidity buffer expressed in days of current GMV."),
    ("settlement_cycle_days", "int64", "Assumed payment settlement cycle (T+N) in days."),
    ("weekly_seasonality_profile", "string", "Coarse tag describing the archetype's weekly pattern."),
]

DAILY_OBSERVATIONS_SCHEMA = [
    ("merchant_id", "string", "Foreign key to merchants.merchant_id."),
    ("date", "date", "Calendar date of the observation."),
    ("day_index", "int64", "0-based day offset from the run's start date. Convenience key, monotonic per merchant."),
    ("gmv", "float64", "Gross merchandise value for the day. Never negative."),
    ("transaction_count", "int64", "Number of transactions. Never negative, floor of 1."),
    ("aov", "float64", "Realized average order value for the day (gmv / transaction_count)."),
    ("refund_count", "int64", "Number of refunded transactions. Never negative."),
    ("refund_amount", "float64", "Total refunded amount. Never negative, never exceeds gmv."),
    ("refund_rate", "float64", "refund_count / transaction_count."),
    ("chargeback_count", "int64", "Number of chargebacks initiated. Never negative."),
    ("chargeback_amount", "float64", "Total chargeback amount. Never negative."),
    ("chargeback_rate", "float64", "chargeback_count / transaction_count."),
    ("fulfillment_delay_avg_days", "float64", "Average fulfillment delay in days for the day's orders. Never negative."),
    ("fulfillment_on_time_rate", "float64", "Fraction of the day's orders fulfilled on time. In [0, 1]."),
    ("customer_count", "int64", "Distinct customers transacting that day. Never negative."),
    ("new_customers", "int64", "Customers transacting for the first time. Never negative."),
    ("returning_customers", "int64", "customer_count - new_customers. Never negative."),
    ("new_customer_rate", "float64", "new_customers / customer_count."),
    ("pct_pay_card", "float64", "Share of the day's GMV paid via card."),
    ("pct_pay_upi", "float64", "Share of the day's GMV paid via UPI."),
    ("pct_pay_netbanking", "float64", "Share of the day's GMV paid via netbanking."),
    ("pct_pay_wallet", "float64", "Share of the day's GMV paid via wallet."),
    ("pct_pay_bnpl", "float64", "Share of the day's GMV paid via BNPL."),
    ("liquidity_balance", "float64", "Simplified mean-reverting settled-funds buffer. Floored at 0."),
    ("pending_settlement_amount", "float64", "Simplified rolling not-yet-settled amount, based on settlement_cycle_days. Never negative."),
]

EVENTS_SCHEMA = [
    ("event_id", "string", "Stable synthetic event identifier, e.g. E000123."),
    ("merchant_id", "string", "Foreign key to merchants.merchant_id."),
    ("event_type", "string", "One of the 9 event types in config.EVENT_TYPES."),
    ("category", "string", "risk | benign_growth."),
    ("hard_negative", "bool", "True for benign_growth events explicitly designed as growth-without-risk cases."),
    ("shape", "string", "gradual | sudden — onset ramp shape."),
    ("start_date", "date", "First day the event has nonzero effect."),
    ("end_date", "date", "Last day of the event's plateau/peak phase before decay, clipped to the run window."),
    ("recovery_end_date", "date", "Last day of the post-event decay tail, clipped to the run window."),
    ("duration_days", "int64", "Nominal event duration (onset + plateau), before the recovery tail."),
    ("severity_score", "float64", "Normalized 0-1 severity draw for this event instance."),
    ("affects", "string", "Comma-separated list of daily_observations metrics this event perturbs."),
    ("description", "string", "Auto-generated human-readable summary."),
]

LABELS_SCHEMA = [
    ("merchant_id", "string", "Foreign key to merchants.merchant_id."),
    ("as_of_date", "date", "Prediction date t. Only rows with a full future window are included."),
    ("day_index", "int64", "day_index of as_of_date."),
    ("horizon_days", "int64", "7 | 14 | 30."),
    ("future_chargeback_amount", "float64", "Sum of chargeback_amount over (t, t+horizon]. Uses future data only."),
    ("future_chargeback_rate", "float64", "Volume-weighted chargeback rate over (t, t+horizon]."),
    ("future_transaction_count", "int64", "Sum of transaction_count over (t, t+horizon]."),
    ("baseline_daily_gmv_trailing", "float64", "Mean daily gmv over the trailing window ending at t (uses only data at/before t)."),
    ("baseline_daily_chargeback_amount_trailing", "float64", "Mean daily chargeback_amount over the trailing window ending at t."),
    ("baseline_chargeback_rate_trailing", "float64", "Volume-weighted chargeback rate over the trailing window ending at t."),
    ("elevation_ratio_amount", "float64", "future_chargeback_amount / (baseline_daily_chargeback_amount_trailing * horizon_days), guarded against div-by-~0."),
    ("elevation_ratio_rate", "float64", "future_chargeback_rate / baseline_chargeback_rate_trailing, guarded against div-by-~0."),
    ("label_elevated_chargeback", "int64", "1 if this future window is a materially elevated chargeback-loss episode, else 0. See config.py thresholds."),
]

TABLES = {
    "merchants": MERCHANTS_SCHEMA,
    "daily_observations": DAILY_OBSERVATIONS_SCHEMA,
    "events": EVENTS_SCHEMA,
    "labels": LABELS_SCHEMA,
}


def columns(table_name: str) -> list[str]:
    return [c for c, _, _ in TABLES[table_name]]


def as_json_schema() -> dict:
    return {
        table: [
            {"name": name, "dtype": dtype, "description": desc}
            for name, dtype, desc in cols
        ]
        for table, cols in TABLES.items()
    }
