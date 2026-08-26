"""
Causal (trailing/expanding-only) computation primitives.

Every function here takes a DataFrame already sorted by
(merchant_id, day_index) and returns a Series aligned to the input's index.
All windows are trailing and INCLUSIVE of the current row — i.e. computing
the value "as of day t" uses day_index in [t-window+1, t], never t+1 or
later. This matches the generator's own trailing-window convention
(ml/data_generation/labels.py) and is what makes every derived feature a
function of (merchant_id, day <= t) only.

Grouping is done with pandas' groupby(...).transform()/rolling(), which
processes each merchant's series independently — no cross-merchant leakage
is possible even accidentally, since one merchant's rows never enter
another's rolling window.
"""

from __future__ import annotations

import pandas as pd

from .config import RATIO_DENOM_FLOOR, RECENCY_CAP_DAYS, STD_FLOOR, Z_SCORE_CLIP


def _grouped(df: pd.DataFrame):
    return df.groupby("merchant_id", sort=False)


def rolling_sum(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    return _grouped(df)[col].transform(lambda s: s.rolling(window, min_periods=1).sum())


def rolling_mean(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    return _grouped(df)[col].transform(lambda s: s.rolling(window, min_periods=1).mean())


def rolling_std(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    std = _grouped(df)[col].transform(lambda s: s.rolling(window, min_periods=1).std())
    return std.fillna(0.0)


def rolling_volume_weighted_rate(df: pd.DataFrame, numerator_col: str, denominator_col: str, window: int) -> pd.Series:
    """sum(numerator) / sum(denominator) over the trailing window — the
    volume-weighted way to aggregate a rate across days, so a handful of
    high-volume days aren't swamped by many low-volume/zero days (or vice
    versa). This is deliberately NOT a mean of the daily rate column.
    """
    num_sum = rolling_sum(df, numerator_col, window)
    den_sum = rolling_sum(df, denominator_col, window)
    return num_sum / den_sum.clip(lower=RATIO_DENOM_FLOOR)


def rolling_weighted_mean(df: pd.DataFrame, value_col: str, weight_col: str, window: int) -> pd.Series:
    """Volume-weighted rolling mean of a per-day RATE column (e.g.
    fulfillment_on_time_rate) that has no raw numerator/denominator pair of
    its own in the schema — weights each day's rate by that day's volume
    (weight_col) before averaging, so a 1-transaction day doesn't count as
    much as a 100-transaction day.
    """
    weighted_sum = rolling_sum(df.assign(_w=df[value_col] * df[weight_col]), "_w", window)
    weight_sum = rolling_sum(df, weight_col, window)
    return weighted_sum / weight_sum.clip(lower=RATIO_DENOM_FLOOR)


def expanding_mean_of_series(df: pd.DataFrame, series: pd.Series, min_periods: int = 1) -> pd.Series:
    """Expanding (inception-to-date, day 0..t) mean of an already-computed
    per-row series (e.g. a 28d rolling rate), grouped by merchant.
    """
    tmp = df[["merchant_id"]].copy()
    tmp["_v"] = series.values
    return tmp.groupby("merchant_id", sort=False)["_v"].transform(lambda s: s.expanding(min_periods=min_periods).mean())


def expanding_std_of_series(df: pd.DataFrame, series: pd.Series, min_periods: int = 1) -> pd.Series:
    tmp = df[["merchant_id"]].copy()
    tmp["_v"] = series.values
    std = tmp.groupby("merchant_id", sort=False)["_v"].transform(lambda s: s.expanding(min_periods=min_periods).std())
    return std.fillna(0.0)


def deviation_zscore(df: pd.DataFrame, current_series: pd.Series, baseline_series_for_expanding: pd.Series) -> pd.Series:
    """(current - expanding_baseline_mean) / expanding_baseline_std, floored
    and clipped for numerical safety. `baseline_series_for_expanding` is
    typically a smoothed (e.g. 28d-rolling) version of the same metric, so
    the baseline itself isn't dominated by single-day low-count noise.
    """
    baseline_mean = expanding_mean_of_series(df, baseline_series_for_expanding)
    baseline_std = expanding_std_of_series(df, baseline_series_for_expanding).clip(lower=STD_FLOOR)
    z = (current_series - baseline_mean) / baseline_std
    return z.clip(lower=-Z_SCORE_CLIP, upper=Z_SCORE_CLIP)


def velocity_diff(short_series: pd.Series, long_series: pd.Series) -> pd.Series:
    """Percentage-point-style velocity for rate metrics already in [0,1] —
    a plain difference, not a ratio (a ratio would blow up when the
    long-window rate is near zero, which is common for chargeback/refund
    rates).
    """
    return short_series - long_series


def velocity_ratio(short_series: pd.Series, long_series: pd.Series) -> pd.Series:
    """Relative-growth velocity for scale metrics (GMV, transaction count),
    which are always > 0 by construction — a ratio is the natural,
    scale-invariant way to express "growing/shrinking" here.
    """
    return short_series / long_series.clip(lower=RATIO_DENOM_FLOOR) - 1.0


def days_since_last_positive(df: pd.DataFrame, count_col: str, cap: int = RECENCY_CAP_DAYS) -> pd.Series:
    """Days since the most recent day (<= t, inclusive) where count_col > 0,
    for the same merchant. Capped at `cap` for merchants with no such day
    yet in their observed history so far.
    """
    tmp = df[["merchant_id", "day_index", count_col]].copy()

    def _per_merchant(g: pd.DataFrame) -> pd.Series:
        last_positive_day = g["day_index"].where(g[count_col] > 0)
        last_positive_day = last_positive_day.ffill()
        days_since = g["day_index"] - last_positive_day
        days_since = days_since.fillna(cap)
        return days_since.clip(upper=cap)

    return tmp.groupby("merchant_id", sort=False, group_keys=False).apply(_per_merchant)


def payment_mix_weighted_shares(df: pd.DataFrame, methods: list[str], window: int) -> dict[str, pd.Series]:
    """GMV-dollar-weighted share of each payment method over the trailing
    window: sum(pct_pay_m * gmv) / sum(gmv). More correct than a plain mean
    of daily shares when daily GMV varies.
    """
    gmv_sum = rolling_sum(df, "gmv", window)
    shares = {}
    for m in methods:
        col = f"pct_pay_{m}"
        weighted = rolling_sum(df.assign(_w=df[col] * df["gmv"]), "_w", window)
        shares[m] = weighted / gmv_sum.clip(lower=RATIO_DENOM_FLOOR)
    return shares


def hhi(shares: dict[str, pd.Series]) -> pd.Series:
    total = None
    for s in shares.values():
        sq = s**2
        total = sq if total is None else total + sq
    return total


def l1_drift(shares_a: dict[str, pd.Series], shares_b: dict[str, pd.Series]) -> pd.Series:
    total = None
    for method in shares_a:
        diff = (shares_a[method] - shares_b[method]).abs()
        total = diff if total is None else total + diff
    return total
