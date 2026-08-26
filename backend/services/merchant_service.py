"""
Merchant data access: list/profile/historical observations/feature vector.

Deliberately excludes merchants.csv's `baseline_*` columns (and
`annual_growth_rate`, `volatility_factor`) from every API-facing response.
Those are the synthetic generator's ground-truth simulation parameters —
not observable business attributes, and exposing them would leak the
"answer key" the model itself never sees (the same reasoning already
documented in docs/architecture/feature_engineering.md and the dataset
validation report's leakage audit).
"""

from __future__ import annotations

from datetime import date

from backend.api.state import AppState
from backend.services.lookups import require_merchant, resolve_day_index

# The only merchants.csv columns considered legitimate business-facing
# profile attributes. Everything else (baseline_*, annual_growth_rate,
# volatility_factor) is a generator-internal parameter, never exposed.
PROFILE_COLUMNS = ["merchant_id", "archetype", "business_tier", "signup_date", "weekly_seasonality_profile"]


def list_merchants(state: AppState, archetype: str | None = None) -> list[dict]:
    df = state.merchants[PROFILE_COLUMNS].copy()
    if archetype is not None:
        df = df[df["archetype"] == archetype]
    df = df.sort_values("merchant_id")
    return [
        {
            "merchant_id": row["merchant_id"],
            "archetype": row["archetype"],
            "business_tier": row["business_tier"],
            "signup_date": row["signup_date"].date().isoformat(),
        }
        for _, row in df.iterrows()
    ]


def get_merchant_profile(state: AppState, merchant_id: str) -> dict:
    row = require_merchant(state.merchants, merchant_id)

    merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id].sort_values("day_index")
    latest = merchant_daily.iloc[-1]

    return {
        "merchant_id": row["merchant_id"],
        "archetype": row["archetype"],
        "business_tier": row["business_tier"],
        "signup_date": row["signup_date"].date().isoformat(),
        "weekly_seasonality_profile": row["weekly_seasonality_profile"],
        "benchmark_history": {
            "first_date": merchant_daily["date"].min().date().isoformat(),
            "last_date": merchant_daily["date"].max().date().isoformat(),
            "n_days": int(len(merchant_daily)),
        },
        "latest_observed_snapshot": {
            "as_of_date": latest["date"].date().isoformat(),
            "day_index": int(latest["day_index"]),
            "gmv": float(latest["gmv"]),
            "transaction_count": int(latest["transaction_count"]),
            "chargeback_rate": float(latest["chargeback_rate"]),
            "refund_rate": float(latest["refund_rate"]),
            "fulfillment_on_time_rate": float(latest["fulfillment_on_time_rate"]),
            "liquidity_balance": float(latest["liquidity_balance"]),
            "provenance": "observed",
        },
    }


def get_observations(
    state: AppState,
    merchant_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
) -> list[dict]:
    require_merchant(state.merchants, merchant_id)
    df = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id].sort_values("day_index")

    if start_date is not None:
        df = df[df["date"].dt.date >= start_date]
    if end_date is not None:
        df = df[df["date"].dt.date <= end_date]
    if limit is not None:
        df = df.tail(limit)

    observation_columns = [c for c in df.columns if c not in ("merchant_id",)]
    records = []
    for _, row in df[observation_columns].iterrows():
        record = row.to_dict()
        record["date"] = row["date"].date().isoformat()
        records.append(record)
    return records


def get_feature_vector(state: AppState, merchant_id: str, as_of_date: date) -> dict:
    require_merchant(state.merchants, merchant_id)
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)

    row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if row.empty:
        # Structurally shouldn't happen (features.csv is built from the same
        # daily_observations rows), but fail loudly rather than silently.
        raise ValueError(f"No feature row for merchant_id={merchant_id} day_index={day_index} despite a matching observation date.")
    row = row.iloc[0]

    features_out = []
    for name in state.feature_columns:
        meta = state.feature_metadata_by_name.get(name, {})
        features_out.append(
            {
                "feature": name,
                "value": float(row[name]),
                "group": meta.get("group", "unknown"),
                "definition": meta.get("definition", "No manifest entry found."),
                "window": meta.get("window"),
                "kind": meta.get("kind", "unknown"),
            }
        )

    return {
        "merchant_id": merchant_id,
        "as_of_date": as_of_date.isoformat(),
        "day_index": day_index,
        "n_features": len(features_out),
        "features": features_out,
    }
