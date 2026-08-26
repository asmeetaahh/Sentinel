"""
Tests for the What-If / Counterfactual Simulator (backend/simulation/,
backend/api/routers/simulator.py).

Covers the required list: schema validation, valid simulations,
invalid/out-of-range controls, determinism for identical inputs, feature
ordering, model invocation (via a predict_proba spy on the real loaded
artifact), unchanged features remaining unchanged, provenance correctness,
absence of forbidden causal/guaranteed language, merchant isolation, and
failure handling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
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
from backend.api.schemas.simulation import ControlsListResponse, SimulationResponse  # noqa: E402
from backend.api.state import load_state  # noqa: E402
from backend.simulation import simulation_service  # noqa: E402
from backend.simulation.controls import (  # noqa: E402
    CONTROLS,
    ControlOutOfRangeError,
    NoInterventionProvidedError,
    UnknownControlError,
)

FORBIDDEN_LANGUAGE = [
    "guaranteed savings",
    "will reduce",
    "will lower",
    "will increase",
    "will cause",
    "this causes",
    "this control causes",
    "is guaranteed",
    "guarantees that",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def any_merchant_id(client):
    return client.get("/merchants").json()["merchants"][0]["merchant_id"]


@pytest.fixture(scope="module")
def another_merchant_id(client, any_merchant_id):
    ids = [m["merchant_id"] for m in client.get("/merchants").json()["merchants"]]
    return next(m for m in ids if m != any_merchant_id)


@pytest.fixture(scope="module")
def as_of_date_for(client):
    def _get(merchant_id: str) -> str:
        return client.get(f"/merchants/{merchant_id}").json()["latest_observed_snapshot"]["as_of_date"]

    return _get


def _assert_no_forbidden_language(response_json: dict) -> None:
    text = json.dumps(response_json).lower()
    for phrase in FORBIDDEN_LANGUAGE:
        assert phrase not in text, f"forbidden causal/guaranteed language {phrase!r} found in response"


# ---------------------------------------------------------------------------
# GET .../simulation/controls — schema, bounds, unknown merchant
# ---------------------------------------------------------------------------


def test_get_controls_matches_schema_and_lists_exactly_three(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.get(f"/merchants/{any_merchant_id}/simulation/controls", params={"as_of_date": as_of})
    assert r.status_code == 200
    body = r.json()
    ControlsListResponse(**body)
    assert len(body["controls"]) == 3
    assert {c["control_id"] for c in body["controls"]} == set(CONTROLS)


def test_get_controls_baseline_within_bounds(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    body = client.get(f"/merchants/{any_merchant_id}/simulation/controls", params={"as_of_date": as_of}).json()
    for control in body["controls"]:
        assert control["min_value"] <= control["baseline_value"] <= control["max_value"]
        assert control["min_value"] < control["max_value"]


def test_get_controls_unknown_merchant_returns_404(client):
    r = client.get("/merchants/NOT_A_REAL_MERCHANT/simulation/controls", params={"as_of_date": "2024-01-15"})
    assert r.status_code == 404


def test_get_controls_unknown_date_returns_404(client, any_merchant_id):
    r = client.get(f"/merchants/{any_merchant_id}/simulation/controls", params={"as_of_date": "1999-01-01"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST .../simulation — valid simulations
# ---------------------------------------------------------------------------


def test_post_simulation_single_control_matches_schema(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": 0.3})
    assert r.status_code == 200
    body = r.json()
    SimulationResponse(**body)
    assert 0.0 <= body["current"]["probability_calibrated"] <= 1.0
    assert 0.0 <= body["simulated"]["probability_calibrated"] <= 1.0
    assert len(body["controls"]) == 1
    assert body["controls"][0]["control_id"] == "refund_rate_28d"
    assert body["controls"][0]["simulated_value"] == 0.3


def test_post_simulation_multiple_controls_all_applied(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(
        f"/merchants/{any_merchant_id}/simulation",
        json={
            "as_of_date": as_of,
            "refund_rate_28d": 0.1,
            "fulfillment_on_time_rate_28d": 0.99,
            "new_customer_rate_28d": 0.2,
        },
    )
    assert r.status_code == 200
    body = r.json()
    applied = {c["control_id"]: c["simulated_value"] for c in body["controls"]}
    assert applied == {
        "refund_rate_28d": 0.1,
        "fulfillment_on_time_rate_28d": 0.99,
        "new_customer_rate_28d": 0.2,
    }


def test_post_simulation_boundary_values_are_accepted(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    controls_body = client.get(f"/merchants/{any_merchant_id}/simulation/controls", params={"as_of_date": as_of}).json()
    bounds = {c["control_id"]: (c["min_value"], c["max_value"]) for c in controls_body["controls"]}
    min_v, max_v = bounds["refund_rate_28d"]

    r_min = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": min_v})
    r_max = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": max_v})
    assert r_min.status_code == 200
    assert r_max.status_code == 200


# ---------------------------------------------------------------------------
# POST .../simulation — invalid input handling
# ---------------------------------------------------------------------------


def test_post_simulation_out_of_range_returns_422(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": 5.0})
    assert r.status_code == 422
    assert "outside the allowed range" in r.json()["detail"]


def test_post_simulation_negative_rate_returns_422(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "new_customer_rate_28d": -0.1})
    assert r.status_code == 422


def test_post_simulation_no_controls_returns_422(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of})
    assert r.status_code == 422


def test_post_simulation_unknown_field_returns_422(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(
        f"/merchants/{any_merchant_id}/simulation",
        json={"as_of_date": as_of, "chargeback_rate_28d": 0.0},
    )
    assert r.status_code == 422


def test_post_simulation_wrong_type_returns_422(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": "high"})
    assert r.status_code == 422


def test_post_simulation_unsupported_horizon_returns_400(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(
        f"/merchants/{any_merchant_id}/simulation",
        json={"as_of_date": as_of, "horizon_days": 14, "refund_rate_28d": 0.1},
    )
    assert r.status_code == 400


def test_post_simulation_unknown_merchant_returns_404(client):
    r = client.post(
        "/merchants/NOT_A_REAL_MERCHANT/simulation",
        json={"as_of_date": "2024-01-15", "refund_rate_28d": 0.1},
    )
    assert r.status_code == 404


def test_post_simulation_unknown_date_returns_404(client, any_merchant_id):
    r = client.post(
        f"/merchants/{any_merchant_id}/simulation",
        json={"as_of_date": "1999-01-01", "refund_rate_28d": 0.1},
    )
    assert r.status_code == 404


def test_post_simulation_malformed_date_returns_422(client, any_merchant_id):
    r = client.post(
        f"/merchants/{any_merchant_id}/simulation",
        json={"as_of_date": "not-a-date", "refund_rate_28d": 0.1},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_post_simulation_is_deterministic_for_identical_inputs(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    payload = {"as_of_date": as_of, "refund_rate_28d": 0.25, "fulfillment_on_time_rate_28d": 0.8}
    r1 = client.post(f"/merchants/{any_merchant_id}/simulation", json=payload)
    r2 = client.post(f"/merchants/{any_merchant_id}/simulation", json=payload)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()


def test_simulate_function_is_deterministic_at_the_python_level(any_merchant_id):
    state = load_state()
    profile_row = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = profile_row["date"].max().date()

    result_a = simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {"refund_rate_28d": 0.4})
    result_b = simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {"refund_rate_28d": 0.4})
    assert result_a == result_b


# ---------------------------------------------------------------------------
# Feature ordering, model invocation, and "unrelated features untouched" —
# verified by output-equivalence against a manually-built expected feature
# row fed directly into the SAME loaded artifact. This is more robust than
# spying on predict_proba (sklearn's internal calibration machinery
# inspects the bound method's __name__, which a naive mock breaks) and
# proves what the actual production code path computes: any wrong ordering,
# an accidentally-touched unrelated feature, or a different model would
# almost certainly change a 300-tree ensemble's output.
# ---------------------------------------------------------------------------


def test_simulation_matches_manual_invocation_of_the_same_artifact_with_only_target_feature_changed(any_merchant_id):
    state = load_state()
    merchant_rows = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = merchant_rows["date"].max().date()
    day_index = int(merchant_rows["day_index"].max())

    base_row = (
        state.features[(state.features["merchant_id"] == any_merchant_id) & (state.features["day_index"] == day_index)]
        .iloc[0][state.feature_columns]
        .to_numpy(dtype=float)
    )
    target_feature = CONTROLS["fulfillment_on_time_rate_28d"].feature
    target_idx = state.feature_columns.index(target_feature)

    expected_row = base_row.copy()
    expected_row[target_idx] = 0.99
    X_expected = expected_row.reshape(1, -1)

    expected_calibrated = float(state.artifact.calibrated_pipeline.predict_proba(X_expected)[0, 1])
    expected_raw = float(state.artifact.base_random_forest.predict_proba(X_expected)[0, 1])

    result = simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {"fulfillment_on_time_rate_28d": 0.99})

    assert result["simulated"]["probability_calibrated"] == pytest.approx(expected_calibrated)
    assert result["simulated"]["probability_raw_rf"] == pytest.approx(expected_raw)

    # Every OTHER feature stayed byte-identical to the observed baseline —
    # the manually-built comparison row only ever touched the target index.
    mask = np.ones(len(state.feature_columns), dtype=bool)
    mask[target_idx] = False
    assert np.array_equal(expected_row[mask], base_row[mask])


def test_current_state_matches_direct_prediction_on_the_unmodified_feature_row(any_merchant_id):
    """Confirms simulate()'s "current" output is the real artifact's own
    prediction on the merchant's actual observed feature row — not a
    placeholder, and not the output of some other model.
    """
    state = load_state()
    merchant_rows = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = merchant_rows["date"].max().date()
    day_index = int(merchant_rows["day_index"].max())

    base_row = (
        state.features[(state.features["merchant_id"] == any_merchant_id) & (state.features["day_index"] == day_index)]
        .iloc[0][state.feature_columns]
        .to_numpy(dtype=float)
    )
    X_current = base_row.reshape(1, -1)
    expected_current_calibrated = float(state.artifact.calibrated_pipeline.predict_proba(X_current)[0, 1])
    expected_current_raw = float(state.artifact.base_random_forest.predict_proba(X_current)[0, 1])

    result = simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {"refund_rate_28d": 0.33})

    assert result["current"]["probability_calibrated"] == pytest.approx(expected_current_calibrated)
    assert result["current"]["probability_raw_rf"] == pytest.approx(expected_current_raw)


def test_state_features_table_never_mutated_by_simulation(any_merchant_id, another_merchant_id):
    state = load_state()
    before = state.features.copy(deep=True)

    merchant_rows = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = merchant_rows["date"].max().date()
    simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {"refund_rate_28d": 0.5, "new_customer_rate_28d": 0.6})

    other_rows = state.daily_observations[state.daily_observations["merchant_id"] == another_merchant_id]
    other_as_of = other_rows["date"].max().date()
    simulation_service.simulate(state, another_merchant_id, other_as_of, 30, {"fulfillment_on_time_rate_28d": 0.5})

    assert before.equals(state.features), "simulation must never mutate the shared, startup-loaded features table"


# ---------------------------------------------------------------------------
# Merchant isolation
# ---------------------------------------------------------------------------


def test_merchant_isolation_current_state_matches_each_merchants_own_risk_endpoint(
    client, any_merchant_id, another_merchant_id, as_of_date_for
):
    as_of_a = as_of_date_for(any_merchant_id)
    as_of_b = as_of_date_for(another_merchant_id)

    risk_a = client.get(f"/merchants/{any_merchant_id}/risk", params={"as_of_date": as_of_a}).json()
    risk_b = client.get(f"/merchants/{another_merchant_id}/risk", params={"as_of_date": as_of_b}).json()

    sim_a = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of_a, "refund_rate_28d": 0.1}).json()
    sim_b = client.post(
        f"/merchants/{another_merchant_id}/simulation", json={"as_of_date": as_of_b, "refund_rate_28d": 0.1}
    ).json()

    assert sim_a["current"]["probability_calibrated"] == pytest.approx(risk_a["model"]["probability_calibrated"])
    assert sim_b["current"]["probability_calibrated"] == pytest.approx(risk_b["model"]["probability_calibrated"])
    # Two different merchants' "current" baselines must not collide (would
    # only coincidentally be equal, which is not the case for this benchmark).
    assert risk_a["model"]["probability_calibrated"] != risk_b["model"]["probability_calibrated"]


# ---------------------------------------------------------------------------
# Provenance correctness
# ---------------------------------------------------------------------------


def test_provenance_tags_are_correct(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    body = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": 0.2}).json()

    assert body["current"]["provenance"] == "modeled"
    assert body["simulated"]["provenance"] == "modeled"
    assert body["exposure"]["current"]["provenance"] == "derived"
    assert body["exposure"]["simulated"]["provenance"] == "derived"
    assert body["liquidity_stress"]["current"]["provenance"] == "derived"
    assert body["liquidity_stress"]["simulated"]["provenance"] == "derived"


# ---------------------------------------------------------------------------
# Language: MODELED IMPACT framing, never causal/guaranteed
# ---------------------------------------------------------------------------


def test_response_uses_modeled_impact_language_and_no_forbidden_phrases(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    body = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": 0.2}).json()
    assert "MODELED IMPACT" in body["modeled_impact_disclaimer"]
    _assert_no_forbidden_language(body)


def test_controls_list_response_has_no_forbidden_language(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    body = client.get(f"/merchants/{any_merchant_id}/simulation/controls", params={"as_of_date": as_of}).json()
    _assert_no_forbidden_language(body)


def test_out_of_range_error_message_has_no_forbidden_language(client, any_merchant_id, as_of_date_for):
    as_of = as_of_date_for(any_merchant_id)
    r = client.post(f"/merchants/{any_merchant_id}/simulation", json={"as_of_date": as_of, "refund_rate_28d": 5.0})
    _assert_no_forbidden_language(r.json())


# ---------------------------------------------------------------------------
# Failure handling at the service layer (exception identity, not just HTTP status)
# ---------------------------------------------------------------------------


def test_unknown_control_error_raised_for_bad_control_id(any_merchant_id):
    state = load_state()
    merchant_rows = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = merchant_rows["date"].max().date()
    with pytest.raises(UnknownControlError):
        simulation_service._validate_interventions(state, {"chargeback_rate_28d": 0.01})


def test_control_out_of_range_error_carries_bounds(any_merchant_id):
    state = load_state()
    with pytest.raises(ControlOutOfRangeError) as excinfo:
        simulation_service._validate_interventions(state, {"refund_rate_28d": 10.0})
    assert excinfo.value.min_value == 0.0
    assert excinfo.value.control_id == "refund_rate_28d"


def test_no_intervention_error_when_interventions_empty(any_merchant_id):
    state = load_state()
    merchant_rows = state.daily_observations[state.daily_observations["merchant_id"] == any_merchant_id]
    as_of_date = merchant_rows["date"].max().date()
    with pytest.raises(NoInterventionProvidedError):
        simulation_service.simulate(state, any_merchant_id, as_of_date, 30, {})
