"""
Shared domain exceptions and merchant/date resolution helpers used across
backend services. Routers translate these into HTTP errors — services
never know about HTTP.
"""

from __future__ import annotations

from datetime import date

import pandas as pd


class MerchantNotFoundError(Exception):
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        super().__init__(f"Unknown merchant_id: {merchant_id!r}")


class DateNotAvailableError(Exception):
    """Raised when as_of_date is not within this merchant's generated
    benchmark history — i.e. genuinely missing data, not a server error.
    """

    def __init__(self, merchant_id: str, as_of_date: str, valid_range: tuple[str, str]):
        self.merchant_id = merchant_id
        self.as_of_date = as_of_date
        self.valid_range = valid_range
        super().__init__(
            f"No benchmark data for merchant_id={merchant_id!r} on {as_of_date}. "
            f"Valid range for this merchant is {valid_range[0]} to {valid_range[1]}."
        )


class UnsupportedHorizonError(Exception):
    def __init__(self, requested: int, supported: list[int]):
        self.requested = requested
        self.supported = supported
        super().__init__(
            f"horizon_days={requested} is not supported. Only {supported} has a saved, loadable model artifact "
            "— see docs/research/baseline_ml_report.md for research results across all evaluated horizons."
        )


def require_merchant(merchants: pd.DataFrame, merchant_id: str) -> pd.Series:
    match = merchants[merchants["merchant_id"] == merchant_id]
    if match.empty:
        raise MerchantNotFoundError(merchant_id)
    return match.iloc[0]


def resolve_day_index(daily: pd.DataFrame, merchant_id: str, as_of_date: date) -> int:
    """Maps a calendar date to this merchant's day_index in the benchmark,
    raising DateNotAvailableError (not a generic 500) if the date falls
    outside the merchant's generated history.
    """
    merchant_rows = daily[daily["merchant_id"] == merchant_id]
    if merchant_rows.empty:
        raise MerchantNotFoundError(merchant_id)

    match = merchant_rows[merchant_rows["date"].dt.date == as_of_date]
    if match.empty:
        valid_min = merchant_rows["date"].min().date().isoformat()
        valid_max = merchant_rows["date"].max().date().isoformat()
        raise DateNotAvailableError(merchant_id, as_of_date.isoformat(), (valid_min, valid_max))
    return int(match.iloc[0]["day_index"])


def latest_day_index(daily: pd.DataFrame, merchant_id: str) -> int:
    merchant_rows = daily[daily["merchant_id"] == merchant_id]
    if merchant_rows.empty:
        raise MerchantNotFoundError(merchant_id)
    return int(merchant_rows["day_index"].max())
