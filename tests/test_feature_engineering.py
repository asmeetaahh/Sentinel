"""
Tests for the causal feature-engineering pipeline (ml/features).

Covers exactly what the task requires: causality/no-leakage (structural
+ a direct truncation-invariance proof), expected feature count, and basic
value-range sanity. Not a test for every individual feature's exact
formula — those are documented in the manifest instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.build_features import build_feature_manifest_df, build_features, feature_columns, load_inputs

DATA_DIR = REPO_ROOT / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "raw" / "daily_observations.csv").exists(),
    reason="benchmark not found under data/ — run scripts/generate_dataset.py first",
)

REQUIRED_GROUPS = {
    "payment_behavior",
    "refund_behavior",
    "chargeback_behavior",
    "fulfillment",
    "customer_mix",
    "financial_state",
    "merchant_behavior",
    "temporal_velocity",
    "deviation_from_baseline",
}


@pytest.fixture(scope="module")
def inputs():
    return load_inputs(DATA_DIR)


@pytest.fixture(scope="module")
def features(inputs):
    daily, merchants = inputs
    return build_features(daily, merchants)


@pytest.fixture(scope="module")
def manifest(features):
    return build_feature_manifest_df()


# ---------------------------------------------------------------------------
# Feature count / structure
# ---------------------------------------------------------------------------


def test_feature_count_in_target_range(features):
    cols = feature_columns(features)
    assert 50 <= len(cols) <= 70, len(cols)


def test_manifest_matches_output_columns_exactly(features, manifest):
    cols = set(feature_columns(features))
    manifest_names = set(manifest["name"])
    assert cols == manifest_names, (cols ^ manifest_names)


def test_all_required_feature_groups_present(manifest):
    assert set(manifest["group"].unique()) == REQUIRED_GROUPS


def test_every_manifest_entry_has_required_fields(manifest):
    required_fields = {"name", "group", "definition", "source_columns", "window", "kind", "leakage_status"}
    assert required_fields <= set(manifest.columns)
    assert manifest["definition"].apply(lambda s: len(s) > 10).all()
    assert manifest["kind"].isin(["level", "ratio", "velocity", "acceleration", "deviation"]).all()
    assert (manifest["leakage_status"].str.startswith("causal")).all()


def test_no_nan_or_inf_in_any_feature(features):
    cols = feature_columns(features)
    values = features[cols].to_numpy(dtype=float)
    assert not np.isnan(values).any()
    assert not np.isinf(values).any()


def test_pipeline_is_deterministic(inputs):
    daily, merchants = inputs
    a = build_features(daily, merchants)
    b = build_features(daily, merchants)
    pd.testing.assert_frame_equal(a, b)


# ---------------------------------------------------------------------------
# Leakage: structural guarantees
# ---------------------------------------------------------------------------


def test_load_inputs_only_exposes_merchant_id_and_signup_date(inputs):
    _, merchants = inputs
    assert list(merchants.columns) == ["merchant_id", "signup_date"]


def test_no_source_code_reference_to_events_or_labels_files():
    """Structural guard: the pipeline must have no code path that could read
    scenario or label data, not just avoid doing so in practice. Checks for
    the filenames as actual string literals (quoted), not prose mentions in
    comments/docstrings explaining that they are intentionally NOT read.
    """
    features_pkg_dir = REPO_ROOT / "ml" / "features"
    forbidden_literals = ['"events.csv"', "'events.csv'", '"labels.csv"', "'labels.csv'", "label_elevated"]
    for py_file in features_pkg_dir.glob("*.py"):
        text = py_file.read_text()
        for literal in forbidden_literals:
            assert literal not in text, (py_file, literal)


def test_no_forbidden_baseline_columns_in_output(features):
    forbidden_substrings = ["baseline_", "event_type", "event_id", "severity_score", "hard_negative", "elevation_ratio", "future_chargeback"]
    for col in features.columns:
        for bad in forbidden_substrings:
            assert bad not in col, col


# ---------------------------------------------------------------------------
# Leakage: direct causality proof via truncation invariance
# ---------------------------------------------------------------------------


def test_truncation_invariance(inputs):
    """The direct proof of 'no look-ahead': computing features on only the
    first 60 days of daily_observations must reproduce EXACTLY the first 60
    days of features computed on the full run. Every primitive is a
    trailing/expanding window ending at t, so truncating the future tail of
    an already-fixed input cannot change any earlier row — if it did, some
    computation would have to be looking beyond t.
    """
    daily, merchants = inputs
    n_short = 60

    full_features = build_features(daily, merchants)
    truncated_daily = daily[daily["day_index"] < n_short].copy()
    truncated_features = build_features(truncated_daily, merchants)

    full_prefix = (
        full_features[full_features["day_index"] < n_short]
        .sort_values(["merchant_id", "day_index"])
        .reset_index(drop=True)
    )
    truncated_sorted = truncated_features.sort_values(["merchant_id", "day_index"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(full_prefix, truncated_sorted)


# ---------------------------------------------------------------------------
# Value-range sanity (not exhaustive — one check per feature "family")
# ---------------------------------------------------------------------------


def test_rate_features_within_unit_interval(features):
    rate_cols = [c for c in features.columns if any(c.startswith(p) for p in ["chargeback_rate_", "refund_rate_", "fulfillment_on_time_rate_", "new_customer_rate_"]) and "velocity" not in c and "deviation" not in c and "acceleration" not in c]
    assert len(rate_cols) > 0
    for c in rate_cols:
        assert features[c].between(0, 1).all(), c


def test_payment_mix_hhi_within_valid_bounds(features):
    hhi_cols = [c for c in features.columns if c.startswith("payment_mix_hhi_")]
    assert len(hhi_cols) == 3
    for c in hhi_cols:
        # 5 methods: HHI in [1/5, 1]
        assert features[c].between(0.2 - 1e-9, 1.0 + 1e-9).all(), c


def test_deviation_zscores_are_bounded_by_clip(features):
    dev_cols = [c for c in features.columns if c.endswith("_deviation_z")]
    assert len(dev_cols) == 6
    for c in dev_cols:
        assert features[c].between(-10.0001, 10.0001).all(), c


def test_days_since_last_chargeback_is_bounded_and_nonnegative(features):
    assert (features["days_since_last_chargeback"] >= 0).all()
    assert (features["days_since_last_chargeback"] <= 90).all()


def test_merchant_tenure_days_is_positive_and_increases_with_day_index(features):
    assert (features["merchant_tenure_days"] > 0).all()
    for _, g in features.sort_values(["merchant_id", "day_index"]).groupby("merchant_id"):
        assert g["merchant_tenure_days"].is_monotonic_increasing
