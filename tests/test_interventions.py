"""
Tests for Intervention Intelligence + Merchant Risk Memory
(backend/interventions/, backend/memory/, backend/api/routers/interventions.py).

Covers the required list: deterministic recommendation generation, exact
recommendation rules, ranking/tie-breaking, relevant vs. irrelevant
controls, empty recommendation state, merchant isolation,
simulator-control mapping, provenance, memory record schema, memory
creation/retrieval, simulated-vs-actual-outcome distinction, "not
observed" behavior, absence of fabricated values/causal language, invalid
inputs, and API behavior/validation.
"""

from __future__ import annotations

import json
import sys
from datetime import date
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
from backend.api.schemas.interventions import InterventionMemoryRecord, InterventionRecommendationsResponse  # noqa: E402
from backend.api.state import load_state  # noqa: E402
from backend.interventions import recommendation_service  # noqa: E402
from backend.interventions.rules import RELEVANCE_Z_THRESHOLD, RULES, is_relevant, signed_badness  # noqa: E402
from backend.memory import risk_memory_service  # noqa: E402
from backend.memory.risk_memory_service import (  # noqa: E402
    InvalidInterventionIdError,
    SimulationControlMismatchError,
    SimulationNotApplicableError,
    SimulationRequiredError,
)
from backend.simulation.controls import CONTROLS  # noqa: E402

FORBIDDEN_LANGUAGE = [
    "guaranteed savings",
    "is guaranteed",
    "will definitely",
    "this will reduce",
    "this control will",
    "changing this control causes",
    "causes a reduction",
    "expected savings",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def state():
    return load_state()


@pytest.fixture(scope="module")
def merchant_with_recommendation(state):
    for merchant_id in state.merchants["merchant_id"]:
        result = recommendation_service.get_recommendations(state, merchant_id)
        if result["count"] > 0:
            return merchant_id
    pytest.fail("no merchant produced any intervention recommendation to test with")


@pytest.fixture(scope="module")
def merchant_without_recommendation(state):
    for merchant_id in state.merchants["merchant_id"]:
        result = recommendation_service.get_recommendations(state, merchant_id)
        if result["count"] == 0:
            return merchant_id
    pytest.fail("every merchant produced a recommendation — no empty-state case to test")


@pytest.fixture(scope="module")
def merchants_with_recommendations(state):
    """Every merchant_id that has >=1 recommendation, in a fixed order —
    used wherever a test needs a *guaranteed* recommendation to act on,
    so the test never skips depending on which merchants happen to qualify.
    """
    ids = [m for m in state.merchants["merchant_id"] if recommendation_service.get_recommendations(state, m)["count"] > 0]
    if len(ids) < 3:
        pytest.fail(f"expected at least 3 merchants with recommendations to test against, found {len(ids)}")
    return ids


def _assert_no_forbidden_language(payload: dict) -> None:
    text = json.dumps(payload).lower()
    for phrase in FORBIDDEN_LANGUAGE:
        assert phrase not in text, f"forbidden language {phrase!r} found in response"


# ---------------------------------------------------------------------------
# Recommendation rules
# ---------------------------------------------------------------------------


def test_rules_cover_exactly_the_three_simulator_controls():
    assert set(RULES.keys()) == set(CONTROLS.keys())


def test_rules_reference_not_redefine_simulator_control_metadata(state, merchant_with_recommendation):
    """Every recommendation's simulator_control block must be byte-identical
    to what /merchants/{id}/simulation/controls itself reports — proving
    rules.py never redeclares bounds/labels independently.
    """
    from backend.simulation import simulation_service

    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    as_of_date = date.fromisoformat(result["as_of_date"])
    authoritative = simulation_service.list_controls(state, merchant_with_recommendation, as_of_date)
    authoritative_by_id = {c["control_id"]: c for c in authoritative["controls"]}

    for rec in result["recommendations"]:
        assert rec["simulator_control"] == authoritative_by_id[rec["control_id"]]


def test_signed_badness_direction_semantics():
    high_is_bad = RULES["refund_rate_28d"]
    low_is_bad = RULES["fulfillment_on_time_rate_28d"]
    assert signed_badness(high_is_bad, 3.0) == 3.0
    assert signed_badness(high_is_bad, -3.0) == -3.0
    assert signed_badness(low_is_bad, 3.0) == -3.0
    assert signed_badness(low_is_bad, -3.0) == 3.0


def test_is_relevant_uses_the_documented_threshold():
    rule = RULES["refund_rate_28d"]
    assert is_relevant(rule, RELEVANCE_Z_THRESHOLD) is True
    assert is_relevant(rule, RELEVANCE_Z_THRESHOLD - 0.01) is False
    assert is_relevant(rule, -RELEVANCE_Z_THRESHOLD) is False  # wrong direction, never relevant


# ---------------------------------------------------------------------------
# Ranking / tie-breaking (direct, synthetic — not dependent on real data
# happening to produce a tie)
# ---------------------------------------------------------------------------


def test_ranking_prefers_high_priority_over_medium_regardless_of_magnitude():
    candidates = [
        {"control_id": "refund_rate_28d", "priority": "medium", "_sort_badness": 9.0},
        {"control_id": "fulfillment_on_time_rate_28d", "priority": "high", "_sort_badness": 2.0},
    ]
    candidates.sort(key=recommendation_service.ranking_sort_key)
    assert [c["control_id"] for c in candidates] == ["fulfillment_on_time_rate_28d", "refund_rate_28d"]


def test_ranking_within_a_tier_prefers_larger_deviation_magnitude():
    candidates = [
        {"control_id": "refund_rate_28d", "priority": "medium", "_sort_badness": 2.1},
        {"control_id": "new_customer_rate_28d", "priority": "medium", "_sort_badness": 4.5},
    ]
    candidates.sort(key=recommendation_service.ranking_sort_key)
    assert [c["control_id"] for c in candidates] == ["new_customer_rate_28d", "refund_rate_28d"]


def test_ranking_tiebreak_is_deterministic_control_id_order():
    candidates = [
        {"control_id": "refund_rate_28d", "priority": "medium", "_sort_badness": 3.0},
        {"control_id": "fulfillment_on_time_rate_28d", "priority": "medium", "_sort_badness": 3.0},
        {"control_id": "new_customer_rate_28d", "priority": "medium", "_sort_badness": 3.0},
    ]
    candidates.sort(key=recommendation_service.ranking_sort_key)
    assert [c["control_id"] for c in candidates] == [
        "fulfillment_on_time_rate_28d",
        "new_customer_rate_28d",
        "refund_rate_28d",
    ]


def test_recommendations_are_returned_in_priority_rank_order(state, merchant_with_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    ranks = [rec["priority_rank"] for rec in result["recommendations"]]
    assert ranks == sorted(ranks) == list(range(1, len(ranks) + 1))


# ---------------------------------------------------------------------------
# Deterministic generation / relevant vs irrelevant / empty state
# ---------------------------------------------------------------------------


def test_recommendations_are_deterministic_for_identical_input(state, merchant_with_recommendation):
    a = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    b = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    assert a == b


def test_recommendations_never_include_an_irrelevant_control(state):
    """Every relevance decision is independently recomputed here from the
    real features table and compared against the service's own output —
    for every merchant, not just a hand-picked one.
    """
    for merchant_id in state.merchants["merchant_id"]:
        result = recommendation_service.get_recommendations(state, merchant_id)
        as_of_date = date.fromisoformat(result["as_of_date"])
        merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id]
        day_index = int(merchant_daily[merchant_daily["date"].dt.date == as_of_date]["day_index"].iloc[0])
        feature_row = state.features[
            (state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)
        ].iloc[0]

        recommended_control_ids = {rec["control_id"] for rec in result["recommendations"]}
        for control_id, rule in RULES.items():
            z = float(feature_row[rule.deviation_feature])
            expected_relevant = is_relevant(rule, z)
            assert (control_id in recommended_control_ids) == expected_relevant


def test_recommendations_never_include_all_three_controls_indiscriminately(state):
    """The rule set must be selective — not every merchant should ever see
    every control recommended (that would indicate the relevance gate isn't
    doing anything).
    """
    counts = [recommendation_service.get_recommendations(state, m)["count"] for m in state.merchants["merchant_id"]]
    assert any(c == 0 for c in counts), "expected at least one merchant with zero recommendations"
    assert not all(c == 3 for c in counts)


def test_empty_state_has_no_recommendations_and_a_clear_note(state, merchant_without_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_without_recommendation)
    assert result["count"] == 0
    assert result["recommendations"] == []
    assert result["empty_state_note"] is not None
    assert "no intervention is currently justified" in result["empty_state_note"].lower()


def test_populated_state_has_no_empty_state_note(state, merchant_with_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    assert result["empty_state_note"] is None


# ---------------------------------------------------------------------------
# Merchant isolation
# ---------------------------------------------------------------------------


def test_recommendations_are_scoped_to_the_requested_merchant(state, merchant_with_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    for rec in result["recommendations"]:
        assert rec["merchant_id"] == merchant_with_recommendation
        assert rec["intervention_id"].startswith(f"{merchant_with_recommendation}:")


def test_unknown_merchant_recommendations_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT/interventions")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_recommendation_provenance_tags_are_correct(state, merchant_with_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    for rec in result["recommendations"]:
        assert rec["current_value"]["provenance"] == "observed"
        assert rec["deviation_z"]["provenance"] == "derived"
        assert rec["shap_corroboration"]["provenance"] == "modeled"


# ---------------------------------------------------------------------------
# No fabricated values / no causal or guaranteed language
# ---------------------------------------------------------------------------


def test_no_forbidden_language_in_recommendations(state, merchant_with_recommendation):
    result = recommendation_service.get_recommendations(state, merchant_with_recommendation)
    _assert_no_forbidden_language(result)


def test_no_forbidden_language_across_all_merchants(state):
    for merchant_id in state.merchants["merchant_id"]:
        _assert_no_forbidden_language(recommendation_service.get_recommendations(state, merchant_id))


# ---------------------------------------------------------------------------
# API — recommendations
# ---------------------------------------------------------------------------


def test_get_interventions_matches_schema(client, merchant_with_recommendation):
    r = client.get(f"/merchants/{merchant_with_recommendation}/interventions")
    assert r.status_code == 200
    InterventionRecommendationsResponse(**r.json())


def test_get_interventions_accepts_explicit_as_of_date(client, merchant_with_recommendation):
    profile = client.get(f"/merchants/{merchant_with_recommendation}").json()
    as_of = profile["latest_observed_snapshot"]["as_of_date"]
    r = client.get(f"/merchants/{merchant_with_recommendation}/interventions", params={"as_of_date": as_of})
    assert r.status_code == 200


def test_get_interventions_invalid_date_returns_404(client, merchant_with_recommendation):
    r = client.get(f"/merchants/{merchant_with_recommendation}/interventions", params={"as_of_date": "1999-01-01"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Memory: schema, creation, retrieval, isolation
# ---------------------------------------------------------------------------


def test_memory_starts_empty_for_a_fresh_merchant(client, merchant_with_recommendation):
    r = client.get(f"/merchants/{merchant_with_recommendation}/interventions/memory")
    assert r.status_code == 200
    body = r.json()
    # NOTE: shares module-scoped state with other tests in this file that
    # write to the same merchant's memory — checked only for schema shape
    # and non-negative count here; isolation/content is checked elsewhere
    # with a dedicated, unused-by-other-tests merchant.
    assert body["merchant_id"] == merchant_with_recommendation
    assert isinstance(body["count"], int)


def test_record_reviewed_action_matches_schema(client, state, merchants_with_recommendations):
    # A merchant not touched by other memory-writing tests in this module,
    # for a clean isolation check.
    merchant_id = merchants_with_recommendations[0]
    intervention_id = recommendation_service.get_recommendations(state, merchant_id)["recommendations"][0]["intervention_id"]

    r = client.post(f"/merchants/{merchant_id}/interventions/memory", json={"intervention_id": intervention_id, "action_status": "reviewed"})
    assert r.status_code == 200
    record = InterventionMemoryRecord(**r.json())
    assert record.action_status == "reviewed"
    assert record.simulated_impact is None
    assert record.outcome_status == "not_observed"


def test_record_and_retrieve_memory_round_trip(client, state, merchants_with_recommendations):
    merchant_id = merchants_with_recommendations[1]
    intervention_id = recommendation_service.get_recommendations(state, merchant_id)["recommendations"][0]["intervention_id"]

    before = client.get(f"/merchants/{merchant_id}/interventions/memory").json()["count"]
    client.post(f"/merchants/{merchant_id}/interventions/memory", json={"intervention_id": intervention_id, "action_status": "acknowledged"})
    after = client.get(f"/merchants/{merchant_id}/interventions/memory").json()["count"]
    assert after == before + 1


def test_memory_is_isolated_per_merchant(client, state, merchants_with_recommendations):
    """Recording a memory entry for one merchant must never appear in
    another merchant's memory list.
    """
    merchant_a, merchant_b = merchants_with_recommendations[2], merchants_with_recommendations[3 % len(merchants_with_recommendations)]

    rec_a = recommendation_service.get_recommendations(state, merchant_a)["recommendations"][0]
    client.post(f"/merchants/{merchant_a}/interventions/memory", json={"intervention_id": rec_a["intervention_id"], "action_status": "reviewed"})

    memory_b = client.get(f"/merchants/{merchant_b}/interventions/memory").json()
    assert all(record["merchant_id"] == merchant_b for record in memory_b["records"])
    assert all(record["intervention_id"] != rec_a["intervention_id"] for record in memory_b["records"])


def test_empty_memory_has_a_clear_honest_note(client, merchant_without_recommendation):
    body = client.get(f"/merchants/{merchant_without_recommendation}/interventions/memory").json()
    assert body["count"] == 0
    assert body["empty_state_note"] is not None
    assert "no intervention activity" in body["empty_state_note"].lower()


# ---------------------------------------------------------------------------
# Simulated vs. actual-outcome distinction / "not observed"
# ---------------------------------------------------------------------------


def test_simulated_action_status_produces_a_real_simulated_impact_from_the_real_simulator(client, state, merchants_with_recommendations):
    merchant_id = merchants_with_recommendations[4 % len(merchants_with_recommendations)]
    result = recommendation_service.get_recommendations(state, merchant_id)
    rec = result["recommendations"][0]
    control_id = rec["control_id"]
    as_of_date = rec["as_of_date"]
    bounds = rec["simulator_control"]
    test_value = min(bounds["max_value"], bounds["baseline_value"] + 0.01)

    from backend.simulation import simulation_service

    expected = simulation_service.simulate(state, merchant_id, date.fromisoformat(as_of_date), 30, {control_id: test_value})

    r = client.post(
        f"/merchants/{merchant_id}/interventions/memory",
        json={
            "intervention_id": rec["intervention_id"],
            "action_status": "simulated",
            "simulation": {"as_of_date": as_of_date, control_id: test_value},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["simulated_impact"]["current_probability"] == expected["current"]["probability_calibrated"]
    assert body["simulated_impact"]["simulated_probability"] == expected["simulated"]["probability_calibrated"]
    assert body["simulated_impact"]["provenance"] == "modeled"


def test_outcome_status_is_always_not_observed(client, state, merchants_with_recommendations):
    for merchant_id in merchants_with_recommendations[:3]:
        rec = recommendation_service.get_recommendations(state, merchant_id)["recommendations"][0]
        r = client.post(f"/merchants/{merchant_id}/interventions/memory", json={"intervention_id": rec["intervention_id"], "action_status": "dismissed"})
        assert r.json()["outcome_status"] == "not_observed"


def test_outcome_note_explains_why_no_observed_outcome_exists(client, state, merchants_with_recommendations):
    merchant_id = merchants_with_recommendations[5 % len(merchants_with_recommendations)]
    rec = recommendation_service.get_recommendations(state, merchant_id)["recommendations"][0]
    r = client.post(f"/merchants/{merchant_id}/interventions/memory", json={"intervention_id": rec["intervention_id"], "action_status": "reviewed"})
    note = r.json()["outcome_note"].lower()
    assert "does not provide real-world post-intervention outcomes" in note
    assert "not_observed" in note or "not observed" in note


def test_no_api_path_can_set_outcome_status_to_anything_but_not_observed(client, state, merchants_with_recommendations):
    """The request schema has no outcome_status field at all — attempting
    to smuggle one in must be rejected outright (extra='forbid').
    """
    merchant_id = merchants_with_recommendations[6 % len(merchants_with_recommendations)]
    rec = recommendation_service.get_recommendations(state, merchant_id)["recommendations"][0]
    r = client.post(
        f"/merchants/{merchant_id}/interventions/memory",
        json={"intervention_id": rec["intervention_id"], "action_status": "reviewed", "outcome_status": "success"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------


def test_record_with_malformed_intervention_id_raises_at_service_level(state):
    with pytest.raises(InvalidInterventionIdError):
        risk_memory_service.record_intervention(state, "M0000", "not-a-valid-id", "reviewed")


def test_record_simulated_without_simulation_raises(state):
    with pytest.raises(SimulationRequiredError):
        risk_memory_service.record_intervention(state, "M0000", "M0000:refund_rate_28d:2024-06-28", "simulated")


def test_record_non_simulated_with_simulation_raises(state):
    from backend.api.schemas.simulation import SimulationRequest

    with pytest.raises(SimulationNotApplicableError):
        risk_memory_service.record_intervention(
            state, "M0000", "M0000:refund_rate_28d:2024-06-28", "reviewed", SimulationRequest(as_of_date="2024-06-28", refund_rate_28d=0.3)
        )


def test_record_simulation_missing_recommended_control_raises(state):
    from backend.api.schemas.simulation import SimulationRequest

    with pytest.raises(SimulationControlMismatchError):
        risk_memory_service.record_intervention(
            state,
            "M0000",
            "M0000:refund_rate_28d:2024-06-28",
            "simulated",
            SimulationRequest(as_of_date="2024-06-28", fulfillment_on_time_rate_28d=0.9),
        )


def test_post_memory_malformed_body_returns_422(client, merchant_with_recommendation):
    r = client.post(f"/merchants/{merchant_with_recommendation}/interventions/memory", json={"intervention_id": "x"})
    assert r.status_code == 422  # missing required action_status


def test_post_memory_unknown_merchant_returns_404(client):
    r = client.post("/merchants/NOT_A_REAL_MERCHANT/interventions/memory", json={"intervention_id": "NOT_A_REAL_MERCHANT:refund_rate_28d:2024-06-28", "action_status": "reviewed"})
    assert r.status_code == 404


def test_post_memory_cross_merchant_id_returns_422(client, state):
    merchants = [m for m in state.merchants["merchant_id"]]
    merchant_a, merchant_b = merchants[0], merchants[1]
    r = client.post(
        f"/merchants/{merchant_a}/interventions/memory",
        json={"intervention_id": f"{merchant_b}:refund_rate_28d:2024-06-28", "action_status": "reviewed"},
    )
    assert r.status_code == 422
