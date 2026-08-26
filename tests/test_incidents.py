"""
Tests for Incident Mode / Evidence Readiness (backend/incidents/,
backend/evidence/, backend/api/routers/incidents.py).

Covers the required list: incident retrieval, merchant isolation,
deterministic incident generation, valid/invalid incident IDs, reason-code
validation, evidence readiness, missing-evidence handling, prioritization,
provenance, absence of fabricated evidence, absence of any autonomous
submission behavior, and determinism for repeated requests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

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
from backend.api.schemas.incidents import IncidentDetail, IncidentEvidenceResponse, IncidentListResponse  # noqa: E402
from backend.api.state import load_state  # noqa: E402
from backend.evidence import evidence_service  # noqa: E402
from backend.evidence.reason_codes import (  # noqa: E402
    EVENT_TYPE_TO_REASON_CODE,
    REASON_CODE_REQUIRED_EVIDENCE,
    reason_code_for_event_type,
)
from backend.incidents import incident_service  # noqa: E402
from backend.incidents.incident_service import IncidentNotFoundError  # noqa: E402

FORBIDDEN_LANGUAGE = [
    "guaranteed",
    "will submit",
    "has been submitted",
    "dispute filed",
    "we filed",
    "razorpay's internal",
    "razorpay's proprietary",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def state():
    return load_state()


@pytest.fixture(scope="module")
def merchant_with_incidents(client):
    for m in client.get("/merchants").json()["merchants"]:
        r = client.get(f"/merchants/{m['merchant_id']}/incidents")
        if r.json()["count"] > 0:
            return m["merchant_id"]
    pytest.fail("no merchant in the benchmark produced any incidents — investigate the detection rule")


@pytest.fixture(scope="module")
def merchant_without_incidents(client):
    for m in client.get("/merchants").json()["merchants"]:
        r = client.get(f"/merchants/{m['merchant_id']}/incidents")
        if r.json()["count"] == 0:
            return m["merchant_id"]
    pytest.fail("every merchant produced at least one incident — no empty-state case to test")


@pytest.fixture(scope="module")
def all_incidents(state):
    """Every incident across every merchant, computed once per test module
    (each build involves a real SHAP explanation call) and reused by every
    test that needs to check a property across the full incident set —
    rather than every such test recomputing all 50 merchants independently.
    """
    incidents = []
    for merchant_id in state.merchants["merchant_id"]:
        incidents.extend(incident_service.list_incidents(state, merchant_id))
    return incidents


def _assert_no_forbidden_language(payload: dict) -> None:
    text = json.dumps(payload).lower()
    for phrase in FORBIDDEN_LANGUAGE:
        assert phrase not in text, f"forbidden language {phrase!r} found in response"


# ---------------------------------------------------------------------------
# Incident retrieval / schema
# ---------------------------------------------------------------------------


def test_list_incidents_matches_schema(client, merchant_with_incidents):
    r = client.get(f"/merchants/{merchant_with_incidents}/incidents")
    assert r.status_code == 200
    body = r.json()
    IncidentListResponse(**body)
    assert body["count"] == len(body["incidents"])
    assert body["count"] > 0


def test_list_incidents_empty_for_a_merchant_with_none(client, merchant_without_incidents):
    r = client.get(f"/merchants/{merchant_without_incidents}/incidents")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0
    assert body["incidents"] == []


def test_get_incident_detail_matches_schema(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    r = client.get(f"/incidents/{incident_id}")
    assert r.status_code == 200
    IncidentDetail(**r.json())


def test_get_incident_evidence_matches_schema(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    r = client.get(f"/incidents/{incident_id}/evidence")
    assert r.status_code == 200
    IncidentEvidenceResponse(**r.json())


# ---------------------------------------------------------------------------
# Valid / invalid IDs
# ---------------------------------------------------------------------------


def test_unknown_merchant_incidents_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT/incidents")
    assert r.status_code == 404


def test_unknown_incident_id_returns_404(client):
    r = client.get("/incidents/INC-NOT-REAL")
    assert r.status_code == 404
    assert "INC-NOT-REAL" in r.json()["detail"]


def test_get_incident_raises_incident_not_found_error_at_python_level(state):
    with pytest.raises(IncidentNotFoundError):
        incident_service.get_incident(state, "INC-NOT-REAL")


def test_unknown_incident_evidence_returns_404(client):
    r = client.get("/incidents/INC-NOT-REAL/evidence")
    assert r.status_code == 404


def test_benign_growth_event_id_is_not_a_valid_incident(client, state):
    """A hard-negative/benign-growth event was never a candidate incident at
    all — confirms the endpoint doesn't accidentally accept any event_id.
    """
    benign_event_id = state.events[state.events["category"] == "benign_growth"].iloc[0]["event_id"]
    r = client.get(f"/incidents/INC-{benign_event_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Merchant isolation
# ---------------------------------------------------------------------------


def test_incidents_belong_only_to_the_requested_merchant(client, merchant_with_incidents):
    body = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()
    assert all(incident["merchant_id"] == merchant_with_incidents for incident in body["incidents"])


def test_cross_merchant_incident_lookup_is_impossible(client, state):
    """An incident_id constructed from one merchant's event cannot be
    retrieved by requesting a different merchant's incident list — the
    incident detail endpoint returns the correct merchant_id regardless of
    who is browsing.
    """
    all_incidents_by_merchant = {}
    for m in client.get("/merchants").json()["merchants"]:
        body = client.get(f"/merchants/{m['merchant_id']}/incidents").json()
        if body["incidents"]:
            all_incidents_by_merchant[m["merchant_id"]] = body["incidents"][0]["incident_id"]
    assert len(all_incidents_by_merchant) >= 2, "need at least 2 merchants with incidents to test isolation"

    for merchant_id, incident_id in all_incidents_by_merchant.items():
        detail = client.get(f"/incidents/{incident_id}").json()
        assert detail["merchant_id"] == merchant_id


# ---------------------------------------------------------------------------
# Deterministic incident generation / repeated requests
# ---------------------------------------------------------------------------


def test_list_incidents_is_deterministic(client, merchant_with_incidents):
    r1 = client.get(f"/merchants/{merchant_with_incidents}/incidents")
    r2 = client.get(f"/merchants/{merchant_with_incidents}/incidents")
    assert r1.json() == r2.json()


def test_get_incident_is_deterministic(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    r1 = client.get(f"/incidents/{incident_id}")
    r2 = client.get(f"/incidents/{incident_id}")
    assert r1.json() == r2.json()


def test_incident_service_function_is_deterministic_at_python_level(state):
    a = incident_service.list_incidents(state, state.merchants.iloc[0]["merchant_id"])
    b = incident_service.list_incidents(state, state.merchants.iloc[0]["merchant_id"])
    assert a == b


def test_incident_selection_rule_matches_documented_detection_bar(state, all_incidents):
    """Confirms the selection rule really is 'the existing artifact crosses
    its own existing decision_threshold at least once in [start, end]' — not
    some other undocumented rule — by independently recomputing it here
    against the real loaded artifact for every risk event.
    """
    artifact = state.artifact
    risk_events = state.events[state.events["category"] == "risk"]
    expected_incident_ids = set()
    for _, ev in risk_events.iterrows():
        merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == ev["merchant_id"]]
        start_day = int(merchant_daily[merchant_daily["date"] == ev["start_date"]]["day_index"].iloc[0])
        end_day = int(merchant_daily[merchant_daily["date"] == ev["end_date"]]["day_index"].iloc[0])
        for day in range(start_day, end_day + 1):
            row = state.features[(state.features["merchant_id"] == ev["merchant_id"]) & (state.features["day_index"] == day)]
            if row.empty:
                continue
            X = row.iloc[0][state.feature_columns].to_numpy(dtype=float).reshape(1, -1)
            p = float(artifact.calibrated_pipeline.predict_proba(X)[0, 1])
            if p >= artifact.decision_threshold:
                expected_incident_ids.add(f"INC-{ev['event_id']}")
                break

    actual_incident_ids = {incident["incident_id"] for incident in all_incidents}

    assert actual_incident_ids == expected_incident_ids
    assert len(actual_incident_ids) > 0


# ---------------------------------------------------------------------------
# Reason-code validation
# ---------------------------------------------------------------------------


def test_every_risk_event_type_has_a_reason_code_mapping(state):
    risk_event_types = set(state.events[state.events["category"] == "risk"]["event_type"].unique())
    assert risk_event_types == set(EVENT_TYPE_TO_REASON_CODE.keys())


def test_reason_code_for_unknown_event_type_raises():
    with pytest.raises(ValueError):
        reason_code_for_event_type("not_a_real_event_type")


def test_incident_reason_code_is_from_the_controlled_taxonomy(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()
    assert body["reason_code"]["code"] in REASON_CODE_REQUIRED_EVIDENCE
    assert "SYNTHETIC PROTOTYPE" in body["reason_code"]["taxonomy_disclaimer"]
    assert "razorpay" not in body["reason_code"]["taxonomy_disclaimer"].lower() or "not razorpay" in body["reason_code"]["taxonomy_disclaimer"].lower()


def test_incident_event_type_reason_code_mapping_is_consistent(all_incidents):
    for incident in all_incidents:
        expected_code = EVENT_TYPE_TO_REASON_CODE[incident["event_type"]]
        assert incident["reason_code"]["code"] == expected_code


# ---------------------------------------------------------------------------
# Evidence readiness / missing evidence
# ---------------------------------------------------------------------------


def test_evidence_readiness_required_evidence_matches_reason_code(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()
    reason_code = body["reason_code"]["code"]
    assert set(body["evidence_readiness"]["required_evidence"]) == set(REASON_CODE_REQUIRED_EVIDENCE[reason_code])


def test_evidence_readiness_status_consistent_with_available_count(all_incidents):
    for incident in all_incidents:
        evidence = incident["evidence_readiness"]
        if evidence["available_count"] == evidence["required_count"]:
            assert evidence["readiness_status"] == "ready"
        elif evidence["available_count"] == 0:
            assert evidence["readiness_status"] == "insufficient"
        else:
            assert evidence["readiness_status"] == "partial"


def test_missing_evidence_items_are_marked_unavailable(all_incidents):
    for incident in all_incidents:
        evidence = incident["evidence_readiness"]
        missing_categories = set(evidence["missing_evidence"])
        for item in evidence["items"]:
            if item["category"] in missing_categories:
                assert item["required"] is True
                assert item["available"] is False


def test_readiness_status_classification_is_exhaustive_and_correct():
    """`invoice` and `payment_confirmation` are treated as universally
    available in this prototype (see evidence_service.py), and both are
    required by every reason code — so `available_count == 0` cannot occur
    through the real pipeline for any real incident. The status
    CLASSIFICATION logic is still tested exhaustively here, isolated from
    that counting behavior, rather than skipped just because this
    particular benchmark can't naturally produce an "insufficient" incident.
    """
    assert evidence_service.readiness_status_from_counts(4, 4) == "ready"
    assert evidence_service.readiness_status_from_counts(2, 4) == "partial"
    assert evidence_service.readiness_status_from_counts(0, 4) == "insufficient"
    assert evidence_service.readiness_status_from_counts(0, 0) == "ready"  # no required evidence at all -> vacuously ready


def test_evidence_engine_never_naturally_reaches_insufficient_because_two_categories_are_universal(state):
    """Documents, via the real function, WHY 'insufficient' doesn't occur in
    practice: invoice + payment_confirmation are always available and always
    required, so available_count is always >= 2 whenever required_count > 0.
    """
    daily = pd.DataFrame(
        {
            "merchant_id": ["ZZ_TEST"] * 5,
            "day_index": [0, 1, 2, 3, 4],
            "fulfillment_on_time_rate": [0.1, 0.1, 0.1, 0.1, 0.1],
            "transaction_count": [10, 10, 10, 10, 10],
            "refund_count": [0, 0, 0, 0, 0],
        }
    )
    merchant_row = pd.Series({"merchant_id": "ZZ_TEST", "archetype": "D2C Fashion", "business_tier": "small"})
    reason_code = reason_code_for_event_type("fulfillment_degradation")
    result = evidence_service.compute_evidence_readiness(daily, merchant_row, reason_code, 0, 4)
    assert result["available_count"] >= 2
    assert result["readiness_status"] in ("partial", "ready")


def test_no_fabricated_evidence_content_anywhere_in_incident_payload(client, merchant_with_incidents):
    """The evidence engine must never invent an actual document, tracking
    number, invoice number, or message body — only category-level
    availability with a disclosed rationale.
    """
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()
    for item in body["evidence_readiness"]["items"]:
        assert set(item.keys()) == {"category", "label", "required", "available", "rationale", "provenance"}
        # no invented identifiers: no tracking-number-shaped or invoice-number-shaped strings
        assert "TRK" not in item["rationale"]
        assert "INV-" not in item["rationale"]


# ---------------------------------------------------------------------------
# Prioritization
# ---------------------------------------------------------------------------


def test_priority_is_one_of_the_controlled_values(all_incidents):
    for incident in all_incidents:
        assert incident["priority"] in ("high", "medium", "low")


def test_high_priority_always_has_at_least_two_reasons(all_incidents):
    for incident in all_incidents:
        if incident["priority"] == "high":
            assert len(incident["priority_reasons"]) >= 2
        elif incident["priority"] == "medium":
            assert len(incident["priority_reasons"]) == 1
        else:
            assert len(incident["priority_reasons"]) == 0


def test_priority_reasons_are_human_readable_explanations(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()
    for reason in body["priority_reasons"]:
        assert isinstance(reason, str)
        assert len(reason) > 10


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_incident_provenance_tags_are_correct(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()

    assert body["model"]["provenance"] == "modeled"
    assert body["exposure"]["estimate"]["provenance"] == "derived"
    assert body["liquidity"]["available_liquidity"]["provenance"] == "observed"
    assert body["case_summary"]["provenance"] == "derived"
    assert body["scenario_context"]["provenance"] == "synthetic_prototype"

    for item in body["evidence_readiness"]["items"]:
        assert item["provenance"] in ("observed", "derived", "synthetic_prototype")


# ---------------------------------------------------------------------------
# No autonomous submission behavior
# ---------------------------------------------------------------------------


def _all_api_routes():
    """Flattens FastAPI's included-router wrappers to the actual endpoint
    routes — this FastAPI version nests them under
    `_IncludedRouter.include_context.included_router.routes` rather than
    exposing them directly on `app.routes`.
    """
    routes = []
    for r in app.routes:
        if type(r).__name__ == "_IncludedRouter":
            routes.extend(r.include_context.included_router.routes)
        else:
            routes.append(r)
    return routes


def test_no_mutating_incident_routes_exist():
    """The incident/evidence layer exposes GET only — there is no endpoint
    that could submit, file, or otherwise mutate anything externally.
    """
    incident_routes = [
        r for r in _all_api_routes() if getattr(r, "path", "").startswith(("/incidents", "/merchants/{merchant_id}/incidents"))
    ]
    assert incident_routes, "expected at least one incident route to be registered"
    for route in incident_routes:
        assert route.methods <= {"GET", "HEAD", "OPTIONS"}, f"non-GET method found on {route.path}: {route.methods}"


def test_no_forbidden_submission_or_proprietary_claims(client, merchant_with_incidents):
    incident_id = client.get(f"/merchants/{merchant_with_incidents}/incidents").json()["incidents"][0]["incident_id"]
    body = client.get(f"/incidents/{incident_id}").json()
    _assert_no_forbidden_language(body)


def test_workflow_stage_never_claims_submission(all_incidents):
    for incident in all_incidents:
        assert incident["workflow_stage"] in ("evidence_check", "response_ready_for_merchant_review")
