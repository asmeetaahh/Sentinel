"""
Top-level orchestration: merchants -> events -> daily observations -> labels.

The single entry point is generate_dataset(). It is parametrized by
(seed, n_merchants, n_days, start_date) so the same code path produces the
50x180 initial benchmark and, unchanged, a future 500x365 run — see
config.SCALE_TARGET_N_MERCHANTS / SCALE_TARGET_N_DAYS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import DEFAULT_N_DAYS, DEFAULT_N_MERCHANTS, DEFAULT_SEED, DEFAULT_START_DATE
from .events import events_to_rows, schedule_events_for_merchant
from .labels import build_labels
from .merchants import generate_merchants
from .schema import columns
from .timeseries import simulate_merchant_days


@dataclass
class GeneratedDataset:
    seed: int
    n_merchants: int
    n_days: int
    start_date: date
    merchants: pd.DataFrame
    daily_observations: pd.DataFrame
    events: pd.DataFrame
    labels: pd.DataFrame


def generate_dataset(
    seed: int = DEFAULT_SEED,
    n_merchants: int = DEFAULT_N_MERCHANTS,
    n_days: int = DEFAULT_N_DAYS,
    start_date: date = DEFAULT_START_DATE,
) -> GeneratedDataset:
    if n_merchants < 1:
        raise ValueError("n_merchants must be >= 1")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")

    merchants_df = generate_merchants(seed=seed, n_merchants=n_merchants, start_date=start_date)

    all_daily_rows: list[dict] = []
    all_event_rows: list[dict] = []

    for merchant_idx, merchant in enumerate(merchants_df.to_dict("records")):
        events = schedule_events_for_merchant(
            seed=seed, merchant_idx=merchant_idx, merchant_id=merchant["merchant_id"], n_days=n_days
        )
        all_event_rows.extend(events_to_rows(events, start_date=start_date, n_days=n_days))

        daily_rows = simulate_merchant_days(
            seed=seed,
            merchant_idx=merchant_idx,
            merchant=merchant,
            n_days=n_days,
            start_date=start_date,
            events=events,
        )
        all_daily_rows.extend(daily_rows)

    daily_df = pd.DataFrame(all_daily_rows)[columns("daily_observations")]
    events_df = pd.DataFrame(all_event_rows)
    if events_df.empty:
        events_df = pd.DataFrame(columns=columns("events"))
    else:
        events_df = events_df[columns("events")]

    labels_df = build_labels(daily_df)

    return GeneratedDataset(
        seed=seed,
        n_merchants=n_merchants,
        n_days=n_days,
        start_date=start_date,
        merchants=merchants_df,
        daily_observations=daily_df,
        events=events_df,
        labels=labels_df,
    )
