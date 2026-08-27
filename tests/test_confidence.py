"""
Tests for Confidence / Data Quality V1 (backend/risk/confidence_service.py,
exposed via /merchants/{id}/risk's `data_quality` section).

Covers the required list: deterministic classification, sufficient
history, limited history, the feature-coverage/data-quality condition,
merchant isolation, and the absence of any fabricated confidence
percentage or score.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / "data" / "metadata" / "modeling" / "artifacts" / "random_forest_calibrated_30d.joblib").exists(),
    reason="model artifact not found — run scripts/evaluate_calibration.py first",
)

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.api.schemas.risk import DataQualitySection  # noqa: E402
from backend.api.state import load_state  # noqa: E402
from backend.risk import confidence_service, risk_service  # noqa: E402
from ml.features.config import WINDOW_LONG, WINDOW_MEDIUM  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def state():
    return load_state()


@pytest.fixture(scope="module")
def any_merchant_id(state):
    return state.merchants.iloc[0]["merchant_id"]


def _date_at_day_index(state, merchant_id: str, day_index: int) -> date:
    merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id].sort_values("day_index")
    row = merchant_daily[merchant_daily["day_index"] == day_index]
    if row.empty:
        pytest.fail(f"day_index={day_index} not present for {merchant_id} — adjust the test's fixture assumption")
    return row.iloc[0]["date"].date()


# ---------------------------------------------------------------------------
# Policy thresholds are the feature pipeline's own constants, never redeclared
# ---------------------------------------------------------------------------


def test_thresholds_are_the_feature_pipelines_own_window_constants():
    assert confidence_service.HISTORY_PARTIAL_THRESHOLD_DAYS == WINDOW_MEDIUM == 28
    assert confidence_service.HISTORY_FULL_THRESHOLD_DAYS == WINDOW_LONG == 60


# ---------------------------------------------------------------------------
# Deterministic classification
# ---------------------------------------------------------------------------


def test_assess_confidence_is_deterministic(state, any_merchant_id):
    first = confidence_service.assess_confidence(state, any_merchant_id, day_index=179)
    second = confidence_service.assess_confidence(state, any_merchant_id, day_index=179)
    assert first == second


def test_repeated_http_requests_are_byte_identical(client, any_merchant_id):
    r1 = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()["data_quality"]
    r2 = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()["data_quality"]
    assert r1 == r2


# ---------------------------------------------------------------------------
# History-length classification. All 50 merchants share the same observed
# start date (2024-01-01 — see docs/architecture/confidence_data_quality.md
# "Limitations"), so history_days at a fixed as_of_date is the same for
# every merchant; any merchant_id is representative here, not cherry-picked.
# ---------------------------------------------------------------------------


def test_sufficient_history_yields_high_confidence(state, any_merchant_id):
    result = confidence_service.assess_confidence(state, any_merchant_id, day_index=179)  # history_days=180
    assert result["confidence_level"] == "high"
    assert result["history_days"] == 180
    assert result["feature_coverage_status"] == "complete"


def test_history_exactly_at_full_threshold_is_high(state, any_merchant_id):
    day_index = confidence_service.HISTORY_FULL_THRESHOLD_DAYS - 1  # history_days == HISTORY_FULL_THRESHOLD_DAYS exactly
    result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
    assert result["history_days"] == confidence_service.HISTORY_FULL_THRESHOLD_DAYS
    assert result["confidence_level"] == "high"


def test_partial_history_yields_medium_confidence(state, any_merchant_id):
    day_index = confidence_service.HISTORY_PARTIAL_THRESHOLD_DAYS  # history_days = 29, in [28, 60)
    result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
    assert result["confidence_level"] == "medium"
    assert confidence_service.HISTORY_PARTIAL_THRESHOLD_DAYS <= result["history_days"] < confidence_service.HISTORY_FULL_THRESHOLD_DAYS


def test_limited_history_yields_limited_confidence(state, any_merchant_id):
    result = confidence_service.assess_confidence(state, any_merchant_id, day_index=10)  # history_days=11
    assert result["confidence_level"] == "limited"
    assert result["history_days"] == 11
    assert result["history_days"] < confidence_service.HISTORY_PARTIAL_THRESHOLD_DAYS


def test_history_days_equals_day_index_plus_one(state, any_merchant_id):
    for day_index in (0, 5, 27, 59, 179):
        result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
        assert result["history_days"] == day_index + 1


# ---------------------------------------------------------------------------
# Feature-coverage / data-quality condition — a real, tested code path even
# though it never triggers in the current benchmark (ml/features' own
# min_periods=1 primitives guarantee no NaN — see
# docs/architecture/feature_engineering.md). Exercised here with a small,
# synthetic in-memory state, exactly like recommendation_service's
# ranking_sort_key is tested with synthetic candidates independent of real
# merchant data.
# ---------------------------------------------------------------------------


def _fake_state(features_df: pd.DataFrame, feature_columns: list[str]) -> SimpleNamespace:
    return SimpleNamespace(features=features_df, feature_columns=feature_columns)


def test_feature_coverage_incomplete_forces_limited_confidence_even_with_full_history():
    features_df = pd.DataFrame(
        [{"merchant_id": "M_TEST", "day_index": 179, "feat_a": 1.0, "feat_b": float("nan")}]
    )
    fake_state = _fake_state(features_df, ["feat_a", "feat_b"])

    result = confidence_service.assess_confidence(fake_state, "M_TEST", day_index=179)  # history_days=180, would otherwise be "high"
    assert result["feature_coverage_status"] == "incomplete"
    assert result["confidence_level"] == "limited"
    assert any("missing" in reason.lower() for reason in result["reasons"])


def test_feature_coverage_complete_with_full_history_is_high():
    features_df = pd.DataFrame([{"merchant_id": "M_TEST", "day_index": 179, "feat_a": 1.0, "feat_b": 2.0}])
    fake_state = _fake_state(features_df, ["feat_a", "feat_b"])

    result = confidence_service.assess_confidence(fake_state, "M_TEST", day_index=179)
    assert result["feature_coverage_status"] == "complete"
    assert result["confidence_level"] == "high"


# ---------------------------------------------------------------------------
# Merchant isolation — a synthetic two-merchant state proves the function
# reads only the requested merchant's own feature row, never another's.
# (Real benchmark merchants can't demonstrate divergence here because every
# merchant shares the same observed start date — see above.)
# ---------------------------------------------------------------------------


def test_merchant_isolation_reads_only_the_requested_merchants_own_feature_row():
    features_df = pd.DataFrame(
        [
            {"merchant_id": "M_COMPLETE", "day_index": 100, "feat_a": 1.0, "feat_b": 2.0},
            {"merchant_id": "M_INCOMPLETE", "day_index": 100, "feat_a": 1.0, "feat_b": float("nan")},
        ]
    )
    fake_state = _fake_state(features_df, ["feat_a", "feat_b"])

    complete_result = confidence_service.assess_confidence(fake_state, "M_COMPLETE", day_index=100)
    incomplete_result = confidence_service.assess_confidence(fake_state, "M_INCOMPLETE", day_index=100)

    assert complete_result["feature_coverage_status"] == "complete"
    assert incomplete_result["feature_coverage_status"] == "incomplete"


def test_api_level_merchant_isolation_does_not_error_across_merchants(client, state):
    merchant_ids = state.merchants["merchant_id"].tolist()[:2]
    for merchant_id in merchant_ids:
        body = client.get(f"/merchants/{merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()
        assert body["merchant_id"] == merchant_id
        DataQualitySection(**body["data_quality"])


# ---------------------------------------------------------------------------
# No fabricated confidence percentage/score, anywhere
# ---------------------------------------------------------------------------

_PERCENT_NEAR_CONFIDENCE_RE = re.compile(r"\d+(\.\d+)?\s*%\s*confiden|confiden\w*\s*(:|is|of)?\s*\d+(\.\d+)?\s*%", re.IGNORECASE)


def test_data_quality_response_never_contains_a_numeric_confidence_percentage(client, any_merchant_id):
    body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()
    dq = body["data_quality"]

    assert isinstance(dq["confidence_level"], str)
    assert dq["confidence_level"] in ("high", "medium", "limited")
    assert "confidence_score" not in dq
    assert "confidence_percentage" not in dq

    full_text = " ".join(dq["reasons"]) + " " + " ".join(dq["limitations"]) + " " + dq["basis"]
    assert not _PERCENT_NEAR_CONFIDENCE_RE.search(full_text)


def test_confidence_level_is_never_a_number(state, any_merchant_id):
    for day_index in (5, 40, 179):
        result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
        assert isinstance(result["confidence_level"], str)
        assert result["confidence_level"] in ("high", "medium", "limited")


# ---------------------------------------------------------------------------
# Schema / API validation
# ---------------------------------------------------------------------------


def test_data_quality_section_matches_pydantic_schema(client, any_merchant_id):
    body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()
    DataQualitySection(**body["data_quality"])


def test_invalid_confidence_level_rejected_by_schema():
    from pydantic import ValidationError

    valid_kwargs = dict(
        history_days=180,
        history_window_partial_days=28,
        history_window_full_days=60,
        feature_coverage_status="complete",
        reasons=["x"],
        limitations=["y"],
        basis="z",
        provenance="derived",
    )
    with pytest.raises(ValidationError):
        DataQualitySection(confidence_level="very_high", **valid_kwargs)  # not one of high/medium/limited


def test_reasons_and_limitations_are_never_empty(state, any_merchant_id):
    for day_index in (5, 40, 179):
        result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
        assert len(result["reasons"]) > 0
        assert len(result["limitations"]) > 0
        assert result["basis"]


def test_basis_names_the_actual_thresholds_used(state, any_merchant_id):
    result = confidence_service.assess_confidence(state, any_merchant_id, day_index=179)
    assert "28" in result["basis"]
    assert "60" in result["basis"]


def test_provenance_is_derived_never_modeled(state, any_merchant_id):
    for day_index in (5, 40, 179):
        result = confidence_service.assess_confidence(state, any_merchant_id, day_index=day_index)
        assert result["provenance"] == "derived"


def test_risk_endpoint_data_quality_is_present_and_consistent_with_direct_service_call(state, any_merchant_id):
    as_of_date = date(2024, 6, 28)
    expected = risk_service.assess_risk(state, any_merchant_id, as_of_date, 30)["data_quality"]

    with TestClient(app) as client:
        body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-06-28"}).json()

    assert body["data_quality"] == expected
