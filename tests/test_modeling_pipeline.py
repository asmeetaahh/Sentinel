"""
Tests for the baseline ML evaluation pipeline (ml/modeling).

Focused on exactly what matters for trusting the results: merchant-level
split integrity, temporal-cutoff isolation, the warning-lead-time
definition's correctness (a real bug — "earliest positive anywhere in the
lookback window" trivially hit the window boundary and inflated lead times
to the horizon maximum — was found and fixed while building this pipeline;
see warning_lead_time.py's docstring), the shortcut auditor's own
correctness, and basic metric arithmetic. Not a test for every model's
exact hyperparameters.
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

from ml.modeling import datasets, metrics, models, shortcut_audit, splits, warning_lead_time
from ml.modeling.config import SEED, SPLIT_FRACTIONS, TEMPORAL_CUTOFF_DAY_INDEX

DATA_DIR = REPO_ROOT / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "processed" / "features.csv").exists(),
    reason="feature/label artifacts not found — run scripts/build_features.py and scripts/generate_dataset.py first",
)


@pytest.fixture(scope="module")
def tables():
    return datasets.load_raw_tables()


@pytest.fixture(scope="module")
def split_df(tables):
    return splits.build_merchant_split(tables["merchants"], seed=SEED)


# ---------------------------------------------------------------------------
# Merchant-level split integrity
# ---------------------------------------------------------------------------


def test_split_covers_all_merchants_with_no_overlap(tables, split_df):
    assert split_df["merchant_id"].nunique() == len(split_df)
    assert set(split_df["merchant_id"]) == set(tables["merchants"]["merchant_id"])

    by_split = {name: set(g["merchant_id"]) for name, g in split_df.groupby("split")}
    assert by_split["train"].isdisjoint(by_split["val"])
    assert by_split["train"].isdisjoint(by_split["test"])
    assert by_split["val"].isdisjoint(by_split["test"])


def test_split_is_deterministic_given_seed(tables):
    a = splits.build_merchant_split(tables["merchants"], seed=SEED)
    b = splits.build_merchant_split(tables["merchants"], seed=SEED)
    pd.testing.assert_frame_equal(a.sort_values("merchant_id").reset_index(drop=True), b.sort_values("merchant_id").reset_index(drop=True))


def test_different_seed_gives_different_split(tables):
    a = splits.build_merchant_split(tables["merchants"], seed=SEED)
    b = splits.build_merchant_split(tables["merchants"], seed=SEED + 1)
    a_test = set(a[a["split"] == "test"]["merchant_id"])
    b_test = set(b[b["split"] == "test"]["merchant_id"])
    assert a_test != b_test


def test_split_fractions_are_reasonably_close_to_target(split_df):
    summary = splits.split_summary(split_df)
    for name, target in SPLIT_FRACTIONS.items():
        assert abs(summary["overall_fractions"][name] - target) < 0.15, (name, summary["overall_fractions"])


# ---------------------------------------------------------------------------
# Temporal cutoff / stress-test isolation
# ---------------------------------------------------------------------------


def test_train_and_val_never_see_late_period_data(tables, split_df):
    frame = datasets.build_horizon_frame(tables, horizon_days=14)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)
    assert (frames["train"]["day_index"] < TEMPORAL_CUTOFF_DAY_INDEX).all()
    assert (frames["val"]["day_index"] < TEMPORAL_CUTOFF_DAY_INDEX).all()
    assert (frames["normal_test"]["day_index"] < TEMPORAL_CUTOFF_DAY_INDEX).all()


def test_stress_test_uses_only_test_merchants_in_late_period(tables, split_df):
    frame = datasets.build_horizon_frame(tables, horizon_days=14)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)
    test_merchants = set(split_df[split_df["split"] == "test"]["merchant_id"])

    assert set(frames["stress_test"]["merchant_id"]) <= test_merchants
    assert (frames["stress_test"]["day_index"] >= TEMPORAL_CUTOFF_DAY_INDEX).all()


def test_normal_test_and_stress_test_share_no_rows(tables, split_df):
    frame = datasets.build_horizon_frame(tables, horizon_days=7)
    frame = datasets.apply_merchant_split(frame, split_df)
    frames = datasets.train_val_test_frames(frame)
    a = set(zip(frames["normal_test"]["merchant_id"], frames["normal_test"]["day_index"]))
    b = set(zip(frames["stress_test"]["merchant_id"], frames["stress_test"]["day_index"]))
    assert a.isdisjoint(b)


# ---------------------------------------------------------------------------
# Dataset assembly / leakage
# ---------------------------------------------------------------------------


def test_feature_matrix_matches_manifest_exactly(tables):
    feature_cols = datasets.load_feature_columns()
    frame = datasets.build_horizon_frame(tables, horizon_days=30)
    for col in feature_cols:
        assert col in frame.columns
    forbidden = {"merchant_id", "day_index", "as_of_date", "label_elevated_chargeback", "future_chargeback_amount"}
    assert forbidden.isdisjoint(set(feature_cols))


# ---------------------------------------------------------------------------
# Warning lead time — the definition that had a real bug
# ---------------------------------------------------------------------------


def _toy_frame(day_indices, labels):
    return pd.DataFrame({"merchant_id": ["M0"] * len(day_indices), "day_index": day_indices, "label_elevated_chargeback": labels})


def test_long_positive_run_counts_as_one_episode_not_many():
    day_indices = list(range(0, 20))
    labels = [0] * 5 + [1] * 10 + [0] * 5  # one 10-day-long episode, onset at day 5
    predicted = [1] * 20  # model always positive
    frame = _toy_frame(day_indices, labels)
    result = warning_lead_time.compute_warning_lead_times(frame, predicted, horizon_days=7)
    assert result["n_episodes_total"] == 1


def test_sustained_alert_immediately_before_onset_gives_correct_lead_time():
    day_indices = list(range(0, 20))
    labels = [0] * 10 + [1] * 5 + [0] * 5  # onset at day 10
    # model positive on days 6,7,8,9 (immediately before onset), negative elsewhere
    predicted = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1] + [0] * 10
    frame = _toy_frame(day_indices, labels)
    result = warning_lead_time.compute_warning_lead_times(frame, predicted, horizon_days=7)
    assert result["n_episodes_total"] == 1
    assert result["n_early_warning"] == 1
    assert result["median_warning_lead_time_days"] == 4  # onset(10) - run_start(6) = 4


def test_isolated_early_blip_not_connected_to_onset_does_not_count_as_early():
    """Regression test for the exact bug found during development: a single
    positive day far from onset, with negatives in between, must NOT be
    credited as a sustained early warning.
    """
    day_indices = list(range(0, 20))
    labels = [0] * 10 + [1] * 5 + [0] * 5  # onset at day 10
    predicted = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0] + [0] * 10  # one blip at day 1, then quiet
    frame = _toy_frame(day_indices, labels)
    result = warning_lead_time.compute_warning_lead_times(frame, predicted, horizon_days=7)
    assert result["n_early_warning"] == 0
    assert result["n_missed"] == 1


def test_detection_after_onset_is_not_counted_as_a_warning():
    day_indices = list(range(0, 20))
    labels = [0] * 10 + [1] * 5 + [0] * 5  # onset at day 10, runs to day 14
    predicted = [0] * 12 + [1, 1] + [0] * 6  # first fires on day 12, inside the run
    frame = _toy_frame(day_indices, labels)
    result = warning_lead_time.compute_warning_lead_times(frame, predicted, horizon_days=7)
    assert result["n_early_warning"] == 0
    assert result["n_detected_at_or_after_onset"] == 1
    assert result["median_warning_lead_time_days"] is None


def test_lookback_is_bounded_by_horizon():
    """A sustained run that starts more than `horizon_days` before onset
    must be clipped at the horizon boundary, not credited with more lead
    time than the horizon itself.
    """
    day_indices = list(range(0, 30))
    labels = [0] * 20 + [1] * 5 + [0] * 5  # onset at day 20
    predicted = [1] * 30  # positive for the entire series
    frame = _toy_frame(day_indices, labels)
    result = warning_lead_time.compute_warning_lead_times(frame, predicted, horizon_days=7)
    assert result["median_warning_lead_time_days"] == 7


# ---------------------------------------------------------------------------
# Shortcut audit correctness
# ---------------------------------------------------------------------------


def test_audit_flags_forbidden_column_name():
    result = shortcut_audit.audit_feature_columns(["gmv_level_28d", "baseline_chargeback_rate", "event_type_risk"])
    assert not result["passed"]
    assert "baseline_chargeback_rate" in result["forbidden_column_violations"]
    assert "event_type_risk" in result["forbidden_column_violations"]


def test_audit_passes_clean_column_list():
    real_cols = datasets.load_feature_columns()
    result = shortcut_audit.audit_feature_columns(real_cols)
    assert result["passed"]


def test_single_feature_auc_audit_flags_a_column_that_equals_the_label():
    rng = np.random.default_rng(0)
    n = 500
    y = rng.integers(0, 2, size=n)
    noise_col = rng.normal(size=n)
    leak_col = y.astype(float)  # a feature that IS the label
    X = np.column_stack([noise_col, leak_col])
    result = shortcut_audit.single_feature_auc_audit(X, y, ["noise", "leak_equals_label"])
    assert result["any_suspicious"]
    assert "leak_equals_label" in result["suspiciously_high_single_feature_auc"]


# ---------------------------------------------------------------------------
# Metrics arithmetic
# ---------------------------------------------------------------------------


def test_classification_metrics_basic_correctness():
    y_true = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.3, 0.7, 0.6, 0.2, 0.1, 0.05])
    threshold = 0.5
    result = metrics.classification_metrics(y_true, scores, threshold)
    # predicted positive: indices 0,1,3,4 -> tp=2 (idx0,1), fp=2 (idx3,4), fn=1 (idx2), tn=3
    assert result["confusion_matrix"] == {"tn": 3, "fp": 2, "fn": 1, "tp": 2}
    assert result["precision"] == pytest.approx(2 / 4)
    assert result["recall"] == pytest.approx(2 / 3)


def test_false_positive_cost_sensitivity_arithmetic():
    confusion = {"tp": 10, "fp": 5, "fn": 3, "tn": 100}
    result = metrics.false_positive_cost_analysis(confusion)
    assert result["false_positives_per_true_positive"] == pytest.approx(0.5)
    for entry in result["net_value_sensitivity"]:
        expected = entry["assumed_benefit_per_true_positive"] * 10 - result["assumed_cost_per_false_positive"] * 5
        assert entry["net_value_units"] == pytest.approx(expected)


def test_historical_threshold_baseline_only_uses_its_declared_signal_column():
    feature_cols = ["a", "b", "chargeback_rate_deviation_z", "c"]
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 4))
    y = (X[:, 2] > 0.5).astype(int)  # label driven only by the signal column
    model = models.HistoricalThresholdBaseline(feature_cols, "chargeback_rate_deviation_z")
    model.fit(X, y)
    scores = model.predict_score(X)
    np.testing.assert_array_equal(scores, X[:, 2])


# ---------------------------------------------------------------------------
# End-to-end smoke test on the real (committed) benchmark
# ---------------------------------------------------------------------------


def test_full_evaluation_runs_and_produces_expected_structure(tables, split_df):
    from ml.modeling.evaluate import run_full_evaluation

    feature_cols = datasets.load_feature_columns()
    outputs = run_full_evaluation(tables, feature_cols, split_df)

    assert set(outputs.results["by_horizon"].keys()) == {7, 14, 30}
    for h, horizon_result in outputs.results["by_horizon"].items():
        assert horizon_result["n_train"] > 0
        assert horizon_result["n_val"] > 0
        assert horizon_result["n_test"] > 0
        assert "shortcut_audit" in horizon_result
        for model_name in ["historical_threshold_baseline", "logistic_regression", "random_forest"]:
            assert model_name in horizon_result["models"]
            m = horizon_result["models"][model_name]
            assert 0.0 <= m["test"]["pr_auc"] <= 1.0
            assert 0.0 <= m["test"]["precision"] <= 1.0
            assert 0.0 <= m["test"]["recall"] <= 1.0
    assert isinstance(outputs.results["overall_shortcut_audit_pass"], bool)
