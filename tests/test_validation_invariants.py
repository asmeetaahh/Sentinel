"""
A small set of automated guardrails over the COMMITTED on-disk benchmark
(data/), derived from what scripts/validate_dataset.py actually found —
not a test for every subjective distribution shape. See
docs/research/dataset_validation_report.md for the full exploratory
validation these are distilled from.

These load the real dataset on disk rather than regenerating a fixture, so
they also exercise ml/validation/checks.py itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.validation import checks

DATA_DIR = REPO_ROOT / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "raw" / "merchants.csv").exists(),
    reason="committed benchmark not found under data/ — run scripts/generate_dataset.py first",
)


@pytest.fixture(scope="module")
def tables():
    return checks.load_dataset(DATA_DIR)


@pytest.fixture(scope="module")
def tagged_daily(tables):
    return checks.tag_active_event(tables["daily"], tables["events"])


def test_no_duplicates_or_nulls_in_committed_benchmark(tables):
    structure = checks.check_structure(tables)
    assert all(v == 0 for v in structure["duplicates"].values()), structure["duplicates"]
    assert all(len(v) == 0 for v in structure["null_counts"].values()), structure["null_counts"]


def test_no_schema_drift_in_committed_benchmark(tables):
    structure = checks.check_structure(tables)
    assert all(len(v) == 0 for v in structure["schema_column_mismatch"].values()), structure["schema_column_mismatch"]


def test_no_missing_dates_or_day_index_gaps(tables):
    structure = checks.check_structure(tables)
    assert structure["merchants_with_day_index_gaps"] == 0
    assert structure["merchants_with_date_gaps"] == 0


def test_no_self_overlapping_events(tables):
    structure = checks.check_structure(tables)
    assert structure["impossible_or_inconsistent_values"]["self_overlapping_events_per_merchant"] == 0


def test_label_positive_rate_within_sane_band(tables):
    """Regression guard: a future generator/label change that pushes any
    horizon's prevalence outside a broad [5%, 60%] band has moved from
    'imbalanced but usable' to something that needs a fresh look — this
    does not encode a preferred exact rate, only the outer bounds observed
    to be usable during validation.
    """
    label_check = checks.check_labels(tables)
    for h, v in label_check["by_horizon"].items():
        assert 0.05 <= v["positive_rate"] <= 0.60, (h, v["positive_rate"])


def test_archetype_alone_does_not_strongly_predict_label(tables):
    """Guards against a future change accidentally turning archetype into a
    strong shortcut for the label ('Travel merchant = risky'). Ceiling of
    0.75 is deliberately generous — validation observed 0.61-0.65, and mild
    archetype-linked variation is expected (different baseline chargeback
    rates interact with the fixed elevation-ratio threshold), just not a
    near-deterministic one.
    """
    bias_check = checks.check_archetype_bias(tables)
    assert bias_check["max_auc_across_horizons"] < 0.75, bias_check["max_auc_across_horizons"]


def test_growth_does_not_imply_risk_in_committed_benchmark(tables, tagged_daily):
    pooled = checks.pooled_effect_table(tagged_daily, tables["merchants"])
    audit = checks.check_hard_negative_audit(pooled)
    benign = audit["benign_growth_volume_weighted_average"]
    risk = audit["risk_volume_weighted_average"]

    assert benign["gmv_ratio_vs_baseline"] > risk["gmv_ratio_vs_baseline"]
    assert benign["chargeback_rate_ratio_vs_baseline"] < risk["chargeback_rate_ratio_vs_baseline"]
    assert benign["refund_rate_ratio_vs_baseline"] < risk["refund_rate_ratio_vs_baseline"]
    assert benign["chargeback_rate_ratio_vs_baseline"] < 1.5
    assert benign["refund_rate_ratio_vs_baseline"] < 1.5


def test_known_chargeback_exceeds_gmv_simplification_stays_rare(tables):
    """chargeback_amount(t) is modeled against day-t transactions, so it can
    exceed day-t GMV on a low-volume day (see docs). This is a known,
    accepted simplification, not a defect — but it must stay rare. This
    test guards against it silently becoming common.
    """
    structure = checks.check_structure(tables)
    n_days = structure["n_daily_rows"]
    n_exceed = structure["impossible_or_inconsistent_values"]["chargeback_amount_exceeds_gmv_same_day"]
    assert n_exceed / n_days < 0.02, (n_exceed, n_days)


def test_all_financial_and_count_quantities_non_negative(tables):
    structure = checks.check_structure(tables)
    impossible = structure["impossible_or_inconsistent_values"]
    for key in [
        "negative_gmv",
        "negative_transaction_count",
        "negative_refund_amount",
        "negative_chargeback_amount",
        "negative_liquidity_balance",
        "refund_amount_exceeds_gmv",
        "refund_count_exceeds_transactions",
        "chargeback_count_exceeds_transactions",
        "customer_split_inconsistent",
        "aov_times_txn_not_equal_gmv",
        "payment_mix_not_summing_to_one",
    ]:
        assert impossible[key] == 0, key
