"""
Tests for the Sentinel backend API (backend/).

Covers the required list: health, merchant listing, valid/invalid merchant
lookup, historical observations, risk endpoint, unknown prediction date,
SHAP/explanation endpoint, response schema validation, deterministic
repeated requests, and — importantly — that no forbidden/future/internal
data is ever exposed through any response.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

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
from backend.api.schemas.explainability import ExplanationResponse  # noqa: E402
from backend.api.schemas.merchants import MerchantProfileResponse, ObservationsResponse  # noqa: E402
from backend.api.schemas.risk import RiskResponse  # noqa: E402

FORBIDDEN_SUBSTRINGS = [
    "baseline_daily_gmv",
    "baseline_chargeback_rate",
    "baseline_refund_rate",
    "annual_growth_rate",
    "volatility_factor",
    "event_type",
    "event_id",
    "severity_score",
    "hard_negative",
    "elevation_ratio",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def any_merchant_id(client):
    return client.get("/merchants").json()["merchants"][0]["merchant_id"]


def _assert_no_forbidden_content(response_json: dict) -> None:
    text = json.dumps(response_json)
    for bad in FORBIDDEN_SUBSTRINGS:
        assert bad not in text, f"forbidden content {bad!r} found in response"


# ---------------------------------------------------------------------------
# Health / metadata
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metadata_endpoint_exposes_no_filesystem_paths(client):
    r = client.get("/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["horizon_days"] == 30
    assert body["n_features"] == 55
    text = json.dumps(body)
    assert "/Users/" not in text
    assert str(REPO_ROOT) not in text


# ---------------------------------------------------------------------------
# Merchant listing
# ---------------------------------------------------------------------------


def test_list_merchants_returns_all_fifty(client):
    r = client.get("/merchants")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 50
    assert len(body["merchants"]) == 50
    ids = [m["merchant_id"] for m in body["merchants"]]
    assert len(set(ids)) == 50


def test_list_merchants_filter_by_archetype(client):
    r = client.get("/merchants", params={"archetype": "SaaS"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert all(m["archetype"] == "SaaS" for m in body["merchants"])


def test_merchant_list_excludes_forbidden_generator_internals(client):
    r = client.get("/merchants")
    _assert_no_forbidden_content(r.json())


# ---------------------------------------------------------------------------
# Valid / invalid merchant lookup
# ---------------------------------------------------------------------------


def test_get_valid_merchant_matches_schema(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}")
    assert r.status_code == 200
    body = r.json()
    MerchantProfileResponse(**body)  # raises if the shape/types are wrong
    assert body["merchant_id"] == any_merchant_id
    _assert_no_forbidden_content(body)


def test_get_unknown_merchant_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT")
    assert r.status_code == 404
    assert "NOT_A_REAL_MERCHANT" in r.json()["detail"]


def test_get_unknown_merchant_observations_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT/observations")
    assert r.status_code == 404


def test_get_unknown_merchant_risk_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT/risk", params={"as_of_date": "2024-01-15"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Historical observations
# ---------------------------------------------------------------------------


def test_get_observations_matches_schema_and_limit(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}/observations", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    ObservationsResponse(**body)
    assert body["count"] == 10
    assert len(body["observations"]) == 10
    for obs in body["observations"]:
        assert obs["gmv"] >= 0
        assert obs["transaction_count"] >= 1


def test_get_observations_date_range_filter(client, any_merchant_id):
    r = client.get(
        f"/merchants/{any_merchant_id}/observations",
        params={"start_date": "2024-01-01", "end_date": "2024-01-10"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 10
    for obs in body["observations"]:
        assert "2024-01-01" <= obs["date"] <= "2024-01-10"


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------


def test_get_features_returns_55_features(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{any_merchant_id}/features", params={"as_of_date": as_of})
    assert r.status_code == 200
    body = r.json()
    assert body["n_features"] == 55
    assert len(body["features"]) == 55


def test_get_features_unknown_date_returns_404(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}/features", params={"as_of_date": "2099-01-01"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Risk endpoint
# ---------------------------------------------------------------------------


def test_risk_endpoint_matches_schema(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of})
    assert r.status_code == 200
    body = r.json()
    RiskResponse(**body)

    assert 0.0 <= body["model"]["probability_calibrated"] <= 1.0
    assert 0.0 <= body["model"]["probability_raw_rf"] <= 1.0
    assert body["model"]["risk_state"] in ("elevated", "normal")
    assert body["model"]["provenance"] == "modeled"
    assert body["exposure"]["estimate"]["provenance"] == "derived"
    assert body["liquidity"]["available_liquidity"]["provenance"] == "observed"
    assert body["liquidity"]["liquidity_stress"]["provenance"] == "derived"
    assert body["data_quality"]["confidence_level"] in ("high", "medium", "limited")
    assert body["data_quality"]["provenance"] == "derived"


def test_risk_endpoint_disclaimer_present_and_not_overclaiming(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of}).json()
    disclaimer = body["model"]["disclaimer"].lower()
    assert "not a validated real-world probability" in disclaimer


def test_risk_endpoint_unsupported_horizon_returns_400(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of, "horizon_days": 14})
    assert r.status_code == 400


def test_risk_endpoint_unknown_prediction_date_returns_404(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "1999-01-01"})
    assert r.status_code == 404
    assert "Valid range" in r.json()["detail"]


def test_risk_endpoint_malformed_date_returns_422(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "not-a-date"})
    assert r.status_code == 422


def test_retrospective_actual_unavailable_for_recent_dates_near_end_of_benchmark(client, any_merchant_id):
    """The synthetic benchmark's future is fixed and finite — for the most
    recent dates, no future window exists, so retrospective_actual must be
    explicitly unavailable, never fabricated.
    """
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]  # the very last generated day
    body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of}).json()
    assert body["exposure"]["retrospective_actual"]["available"] is False
    assert body["exposure"]["retrospective_actual"]["value"] is None


def test_retrospective_actual_available_for_older_dates(client, any_merchant_id):
    body = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": "2024-02-01"}).json()
    assert body["exposure"]["retrospective_actual"]["available"] is True
    assert isinstance(body["exposure"]["retrospective_actual"]["value"], (int, float))


# ---------------------------------------------------------------------------
# Explanation (SHAP) endpoint
# ---------------------------------------------------------------------------


def test_explanation_endpoint_matches_schema(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of})
    assert r.status_code == 200
    body = r.json()
    ExplanationResponse(**body)

    assert body["faithfulness"]["faithful"] is True
    assert body["faithfulness"]["reconstruction_error"] < 1e-4
    for driver in body["drivers"]["top_positive_contributors"]:
        assert driver["shap_value"] > 0
        assert driver["direction"] == "increases_risk"
    for driver in body["drivers"]["top_negative_contributors"]:
        assert driver["shap_value"] < 0
        assert driver["direction"] == "decreases_risk"
    assert "causal" in body["causality_disclaimer"].lower() or "does not establish" in body["causality_disclaimer"].lower()


def test_explanation_top_k_is_respected(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of, "top_k": 3})
    body = r.json()
    assert len(body["drivers"]["top_positive_contributors"]) <= 3
    assert len(body["drivers"]["top_negative_contributors"]) <= 3


def test_explanation_all_contributors_covers_all_features(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    body = client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of}).json()
    assert len(body["all_contributors"]) == 55


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_repeated_risk_requests_are_deterministic(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r1 = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of}).json()
    r2 = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of}).json()
    assert r1 == r2


def test_repeated_explanation_requests_are_deterministic(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r1 = client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of}).json()
    r2 = client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of}).json()
    assert r1 == r2


# ---------------------------------------------------------------------------
# No forbidden/future data exposure
# ---------------------------------------------------------------------------


def test_no_forbidden_content_across_all_endpoints(client, any_merchant_id):
    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]

    responses = [
        client.get("/health").json(),
        client.get("/metadata").json(),
        client.get("/merchants").json(),
        profile,
        client.get(f"/merchants/{any_merchant_id}/observations", params={"limit": 5}).json(),
        client.get(f"/merchants/{any_merchant_id}/features", params={"as_of_date": as_of}).json(),
        client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of}).json(),
        client.get(f"/merchants/{any_merchant_id}/explanation", params={"as_of_date": as_of}).json(),
    ]
    for body in responses:
        _assert_no_forbidden_content(body)


def test_feature_vector_only_contains_manifest_features(client, any_merchant_id):
    import json as _json

    manifest = _json.loads((REPO_ROOT / "data" / "metadata" / "feature_manifest.json").read_text())
    expected = set(manifest["feature_columns"])

    profile = client.get(f"/merchants/{any_merchant_id}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    body = client.get(f"/merchants/{any_merchant_id}/features", params={"as_of_date": as_of}).json()
    actual = {f["feature"] for f in body["features"]}
    assert actual == expected
