"""
Tests for the synthetic merchant data generator (ml/data_generation).

Covers exactly the properties PROJECT_CONTEXT.md requires of the benchmark:
reproducibility, expected sizing, valid ranges, non-negative financial
quantities, scenario generation, hard-negative (healthy-growth) generation,
and absence of obvious look-ahead / future leakage.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.data_generation import config as cfg
from ml.data_generation.generator import GeneratedDataset, generate_dataset
from ml.data_generation.schema import columns as schema_columns

SMALL_SEED = 42
SMALL_N_MERCHANTS = 12
SMALL_N_DAYS = 90
START_DATE = date(2024, 1, 1)


@pytest.fixture(scope="module")
def small_dataset() -> GeneratedDataset:
    return generate_dataset(seed=SMALL_SEED, n_merchants=SMALL_N_MERCHANTS, n_days=SMALL_N_DAYS, start_date=START_DATE)


@pytest.fixture(scope="module")
def benchmark_dataset() -> GeneratedDataset:
    """The actual initial-benchmark configuration (50 x 180), used for the
    scenario-taxonomy and hard-negative statistical checks, which need
    enough events pooled to be stable.
    """
    return generate_dataset(
        seed=cfg.DEFAULT_SEED,
        n_merchants=cfg.DEFAULT_N_MERCHANTS,
        n_days=cfg.DEFAULT_N_DAYS,
        start_date=cfg.DEFAULT_START_DATE,
    )


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


def test_reproducibility_same_seed_identical_output():
    a = generate_dataset(seed=7, n_merchants=SMALL_N_MERCHANTS, n_days=SMALL_N_DAYS, start_date=START_DATE)
    b = generate_dataset(seed=7, n_merchants=SMALL_N_MERCHANTS, n_days=SMALL_N_DAYS, start_date=START_DATE)

    pd.testing.assert_frame_equal(a.merchants, b.merchants)
    pd.testing.assert_frame_equal(a.daily_observations, b.daily_observations)
    pd.testing.assert_frame_equal(a.events, b.events)
    pd.testing.assert_frame_equal(a.labels, b.labels)


def test_different_seed_changes_output(small_dataset):
    other = generate_dataset(seed=SMALL_SEED + 1, n_merchants=SMALL_N_MERCHANTS, n_days=SMALL_N_DAYS, start_date=START_DATE)
    assert not small_dataset.daily_observations["gmv"].equals(other.daily_observations["gmv"])


# ---------------------------------------------------------------------------
# Expected sizing / schema
# ---------------------------------------------------------------------------


def test_merchant_and_day_counts(small_dataset):
    d = small_dataset
    assert len(d.merchants) == SMALL_N_MERCHANTS
    assert d.merchants["merchant_id"].nunique() == SMALL_N_MERCHANTS

    assert len(d.daily_observations) == SMALL_N_MERCHANTS * SMALL_N_DAYS

    counts = d.daily_observations.groupby("merchant_id").size()
    assert (counts == SMALL_N_DAYS).all()

    for _, group in d.daily_observations.groupby("merchant_id"):
        day_idx = group.sort_values("day_index")["day_index"].to_numpy()
        assert np.array_equal(day_idx, np.arange(SMALL_N_DAYS))


def test_initial_benchmark_sizing_matches_project_context(benchmark_dataset):
    assert benchmark_dataset.n_merchants == 50
    assert benchmark_dataset.n_days == 180
    assert len(benchmark_dataset.daily_observations) == 50 * 180


def test_all_required_archetypes_present(small_dataset):
    assert set(small_dataset.merchants["archetype"].unique()) == set(cfg.ARCHETYPES)


def test_schema_columns_match(small_dataset):
    assert list(small_dataset.merchants.columns) == schema_columns("merchants")
    assert list(small_dataset.daily_observations.columns) == schema_columns("daily_observations")
    assert list(small_dataset.events.columns) == schema_columns("events")
    assert list(small_dataset.labels.columns) == schema_columns("labels")


# ---------------------------------------------------------------------------
# Valid ranges / no negative financial quantities
# ---------------------------------------------------------------------------


def test_rate_columns_within_unit_interval(small_dataset):
    d = small_dataset.daily_observations
    for col in ["refund_rate", "chargeback_rate", "fulfillment_on_time_rate", "new_customer_rate"]:
        assert d[col].between(0, 1).all(), col


def test_payment_mix_sums_to_one(small_dataset):
    d = small_dataset.daily_observations
    pct_cols = [f"pct_pay_{m}" for m in cfg.PAYMENT_METHODS]
    for col in pct_cols:
        assert d[col].between(0, 1).all(), col
    totals = d[pct_cols].sum(axis=1)
    assert np.allclose(totals, 1.0, atol=1e-6)


def test_no_negative_financial_or_count_quantities(small_dataset):
    d = small_dataset.daily_observations
    non_negative_cols = [
        "gmv",
        "transaction_count",
        "refund_count",
        "refund_amount",
        "chargeback_count",
        "chargeback_amount",
        "fulfillment_delay_avg_days",
        "customer_count",
        "new_customers",
        "returning_customers",
        "liquidity_balance",
        "pending_settlement_amount",
        "aov",
    ]
    for col in non_negative_cols:
        assert (d[col] >= 0).all(), col

    assert (d["transaction_count"] >= 1).all()
    assert (d["refund_amount"] <= d["gmv"] + 1e-6).all()
    assert (d["refund_count"] <= d["transaction_count"]).all()
    assert (d["chargeback_count"] <= d["transaction_count"]).all()
    assert (d["new_customers"] + d["returning_customers"] == d["customer_count"]).all()

    labels = small_dataset.labels
    assert (labels["future_chargeback_amount"] >= 0).all()
    assert (labels["future_transaction_count"] >= 0).all()

    merchants = small_dataset.merchants
    for col in ["baseline_daily_gmv", "baseline_aov", "baseline_daily_txn_count", "liquidity_buffer_days"]:
        assert (merchants[col] > 0).all(), col


def test_no_nulls_anywhere(small_dataset):
    assert small_dataset.merchants.isna().sum().sum() == 0
    assert small_dataset.daily_observations.isna().sum().sum() == 0
    assert small_dataset.events.isna().sum().sum() == 0
    assert small_dataset.labels.isna().sum().sum() == 0


# ---------------------------------------------------------------------------
# Scenario / event generation
# ---------------------------------------------------------------------------


def test_event_types_and_categories_match_taxonomy(small_dataset):
    events = small_dataset.events
    assert set(events["event_type"].unique()) <= set(cfg.EVENT_TYPES.keys())
    for event_type, group in events.groupby("event_type"):
        expected_category = cfg.EVENT_TYPES[event_type]
        assert (group["category"] == expected_category).all()
        assert (group["hard_negative"] == (expected_category == cfg.EVENT_CATEGORY_BENIGN_GROWTH)).all()


def test_event_date_ordering_and_bounds(small_dataset):
    d = small_dataset
    events = d.events
    assert (events["start_date"] <= events["end_date"]).all()
    assert (events["end_date"] <= events["recovery_end_date"]).all()
    assert (events["start_date"] >= d.start_date).all()
    last_date = d.start_date + timedelta(days=d.n_days - 1)
    assert (events["recovery_end_date"] <= last_date).all()


def test_events_do_not_self_overlap_per_merchant(small_dataset):
    events = small_dataset.events
    for merchant_id, group in events.groupby("merchant_id"):
        group = group.sort_values("start_date")
        prev_end = None
        for _, row in group.iterrows():
            if prev_end is not None:
                assert row["start_date"] > prev_end, merchant_id
            prev_end = row["recovery_end_date"]


def test_payment_method_shift_never_has_identical_source_and_destination(benchmark_dataset):
    """Regression guard: _sample_severity_params() used to draw
    from_method_idx/to_method_idx independently, so ~1-in-5 instances were a
    silent no-op (recorded as a real scenario with nonzero severity and
    affects=payment_mix,gmv, but zero actual payment-mix effect). Fixed by
    resampling until they differ — see events.py.
    """
    from ml.data_generation.events import schedule_events_for_merchant

    pms_events = benchmark_dataset.events[benchmark_dataset.events["event_type"] == "payment_method_shift"]
    assert len(pms_events) > 0

    merchant_ids = benchmark_dataset.merchants["merchant_id"].tolist()
    for idx, merchant_id in enumerate(merchant_ids):
        events = schedule_events_for_merchant(
            seed=benchmark_dataset.seed, merchant_idx=idx, merchant_id=merchant_id, n_days=benchmark_dataset.n_days
        )
        for ev in events:
            if ev.event_type == "payment_method_shift":
                assert ev.params["from_method_idx"] != ev.params["to_method_idx"], (merchant_id, ev.event_id)


def test_all_nine_event_types_appear_in_benchmark_run(benchmark_dataset):
    observed = set(benchmark_dataset.events["event_type"].unique())
    assert observed == set(cfg.EVENT_TYPES.keys())


def test_gradual_shape_is_the_majority_for_risk_events(benchmark_dataset):
    risk_events = benchmark_dataset.events[benchmark_dataset.events["category"] == cfg.EVENT_CATEGORY_RISK]
    assert len(risk_events) > 0
    gradual_fraction = (risk_events["shape"] == "gradual").mean()
    assert gradual_fraction > 0.5


# ---------------------------------------------------------------------------
# Hard-negative generation: growth must not automatically equal risk
# ---------------------------------------------------------------------------


def _pooled_ratio(daily: pd.DataFrame, merchants: pd.DataFrame, events: pd.DataFrame, event_type: str) -> dict:
    """Volume-weighted realized-vs-expected ratios pooled across all
    instances of one event_type (start_date..recovery_end_date window),
    using each merchant's own static baseline rate as the expectation.
    Pooling many low-count-Poisson event-days is what keeps this stable
    enough to assert on.
    """
    merged = daily.merge(
        merchants[["merchant_id", "baseline_daily_gmv", "baseline_chargeback_rate", "baseline_refund_rate"]],
        on="merchant_id",
    )
    gmv = base_gmv_days = cb_cnt = cb_exp = refund_cnt = refund_exp = 0.0
    for _, ev in events[events["event_type"] == event_type].iterrows():
        sub = merged[
            (merged["merchant_id"] == ev["merchant_id"])
            & (merged["date"] >= ev["start_date"])
            & (merged["date"] <= ev["recovery_end_date"])
        ]
        if sub.empty:
            continue
        gmv += sub["gmv"].sum()
        base_gmv_days += sub["baseline_daily_gmv"].iloc[0] * len(sub)
        cb_cnt += sub["chargeback_count"].sum()
        cb_exp += sub["baseline_chargeback_rate"].iloc[0] * sub["transaction_count"].sum()
        refund_cnt += sub["refund_count"].sum()
        refund_exp += sub["baseline_refund_rate"].iloc[0] * sub["transaction_count"].sum()

    return {
        "gmv_ratio": gmv / base_gmv_days if base_gmv_days else float("nan"),
        "chargeback_ratio": cb_cnt / cb_exp if cb_exp else float("nan"),
        "refund_ratio": refund_cnt / refund_exp if refund_exp else float("nan"),
    }


@pytest.mark.parametrize("event_type", cfg.BENIGN_GROWTH_EVENT_TYPES)
def test_hard_negative_events_grow_without_elevating_risk(benchmark_dataset, event_type):
    d = benchmark_dataset
    ratios = _pooled_ratio(d.daily_observations, d.merchants, d.events, event_type)

    assert ratios["gmv_ratio"] > 1.05, f"{event_type}: expected GMV growth, got {ratios['gmv_ratio']:.3f}"
    # Generous band: pooled but still noisy low-count Poisson data. The
    # point is these stay in a healthy neighborhood of 1.0, in contrast to
    # the risk event types checked below.
    assert ratios["chargeback_ratio"] < 1.6, f"{event_type}: chargeback rate elevated during a benign-growth event ({ratios['chargeback_ratio']:.3f})"
    assert ratios["refund_ratio"] < 1.6, f"{event_type}: refund rate elevated during a benign-growth event ({ratios['refund_ratio']:.3f})"


def test_risk_events_show_clearly_elevated_rates(benchmark_dataset):
    d = benchmark_dataset
    cb_det = _pooled_ratio(d.daily_observations, d.merchants, d.events, "chargeback_deterioration")
    refund_shock = _pooled_ratio(d.daily_observations, d.merchants, d.events, "refund_shock")

    assert cb_det["chargeback_ratio"] > 1.5
    assert refund_shock["refund_ratio"] > 1.5


def test_festival_growth_is_a_clean_healthy_growth_example(benchmark_dataset):
    """The textbook hard negative from PROJECT_CONTEXT.md: GMV rises
    substantially while chargeback/refund health stays normal."""
    d = benchmark_dataset
    ratios = _pooled_ratio(d.daily_observations, d.merchants, d.events, "festival_growth")
    assert ratios["gmv_ratio"] > 1.5
    assert 0.5 < ratios["chargeback_ratio"] < 1.5
    assert 0.5 < ratios["refund_ratio"] < 1.5


# ---------------------------------------------------------------------------
# Absence of obvious future leakage (truncation invariance)
# ---------------------------------------------------------------------------


def test_truncated_run_matches_prefix_of_longer_run():
    """The direct test for 'no look-ahead': generating only the first 60
    days must reproduce EXACTLY the first 60 days of a 120-day run for the
    same seed/merchants — nothing about day t's simulated value may depend
    on how many more days follow it.
    """
    n_short = 60
    n_long = 120
    long_run = generate_dataset(seed=SMALL_SEED, n_merchants=SMALL_N_MERCHANTS, n_days=n_long, start_date=START_DATE)
    short_run = generate_dataset(seed=SMALL_SEED, n_merchants=SMALL_N_MERCHANTS, n_days=n_short, start_date=START_DATE)

    pd.testing.assert_frame_equal(long_run.merchants, short_run.merchants)

    long_prefix = (
        long_run.daily_observations[long_run.daily_observations["day_index"] < n_short]
        .sort_values(["merchant_id", "day_index"])
        .reset_index(drop=True)
    )
    short_all = short_run.daily_observations.sort_values(["merchant_id", "day_index"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(long_prefix, short_all)

    # Events whose *full, unclipped* window fits inside the short window are
    # unaffected by window-edge clipping and must match exactly, including
    # end_date/recovery_end_date.
    long_events = long_run.events.copy()
    long_events["duration_plus_recovery"] = (
        pd.to_datetime(long_events["recovery_end_date"]) - pd.to_datetime(long_events["start_date"])
    ).dt.days
    fully_contained = long_events[
        (pd.to_datetime(long_events["start_date"]) - pd.Timestamp(START_DATE)).dt.days
        + long_events["duration_plus_recovery"]
        < n_short
    ].drop(columns=["duration_plus_recovery"])

    short_events_by_id = short_run.events.set_index("event_id")
    for _, row in fully_contained.iterrows():
        assert row["event_id"] in short_events_by_id.index
        short_row = short_events_by_id.loc[row["event_id"]]
        for col in fully_contained.columns:
            if col == "event_id":
                continue
            assert row[col] == short_row[col], (row["event_id"], col)

    # Labels: any (merchant, as_of_date, horizon) whose full future window
    # fits inside the short run must be byte-identical between runs — this
    # is the leakage guarantee for the label table specifically.
    long_labels = long_run.labels
    fits_in_short = long_labels["day_index"] + long_labels["horizon_days"] <= n_short - 1
    long_labels_subset = (
        long_labels[fits_in_short].sort_values(["merchant_id", "as_of_date", "horizon_days"]).reset_index(drop=True)
    )
    short_labels_subset = (
        short_run.labels.sort_values(["merchant_id", "as_of_date", "horizon_days"]).reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(long_labels_subset, short_labels_subset)


def test_labels_only_cover_horizons_with_full_future_window():
    d = generate_dataset(seed=SMALL_SEED, n_merchants=3, n_days=40, start_date=START_DATE)
    max_day_index = d.n_days - 1
    assert ((d.labels["day_index"] + d.labels["horizon_days"]) <= max_day_index).all()


def test_labels_support_all_three_horizons_and_none_locked_in():
    d = generate_dataset(seed=SMALL_SEED, n_merchants=3, n_days=90, start_date=START_DATE)
    assert set(d.labels["horizon_days"].unique()) == set(cfg.LABEL_HORIZONS_DAYS)


def test_daily_observations_do_not_contain_future_derived_columns(small_dataset):
    # Structural guard: the raw feature-source table must never carry any
    # column derived from the label-construction logic.
    label_only_columns = {
        "future_chargeback_amount",
        "future_chargeback_rate",
        "elevation_ratio_amount",
        "elevation_ratio_rate",
        "label_elevated_chargeback",
    }
    assert label_only_columns.isdisjoint(small_dataset.daily_observations.columns)
