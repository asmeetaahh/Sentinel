"""
Merchant Risk Memory V1 — a lightweight, in-process, no-persistence record
of intervention/simulation activity. See
docs/architecture/intervention_intelligence.md "Merchant Risk Memory" for
the full data model and the three-way simulated/action/outcome distinction
this module exists to enforce.

The store lives on AppState (state.memory_store), reset to empty on every
process (re)start exactly like every other in-memory table this backend
already loads once at startup — no database, per PROJECT_CONTEXT.md's
explicit "do not add a database" instruction for this milestone.

`outcome_status` is ALWAYS "not_observed" for every record this module can
ever produce — there is no code path, parameter, or request field that can
set it to anything else, because the synthetic benchmark provides no
real-world post-intervention outcome to observe. This is enforced here,
not left to caller discipline.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from backend.api.state import AppState
from backend.interventions.rules import RULES
from backend.services.lookups import require_merchant, resolve_day_index
from backend.simulation import simulation_service

OUTCOME_NOTE = (
    "This synthetic benchmark does not provide real-world post-intervention outcomes. Sentinel does not "
    "fabricate, infer, or claim to have observed one — this record remains 'not_observed' until a legitimate "
    "outcome data source exists. See docs/architecture/intervention_intelligence.md."
)

EMPTY_MEMORY_NOTE = (
    "No intervention activity has been recorded for this merchant in this session. Recording is entirely "
    "optional and merchant-initiated — nothing is recorded automatically."
)


class InvalidInterventionIdError(Exception):
    def __init__(self, intervention_id: str, reason: str):
        self.intervention_id = intervention_id
        self.reason = reason
        super().__init__(f"Invalid intervention_id {intervention_id!r}: {reason}")


class SimulationRequiredError(Exception):
    def __init__(self):
        super().__init__("action_status='simulated' requires a 'simulation' body describing what was tested.")


class SimulationNotApplicableError(Exception):
    def __init__(self, action_status: str):
        super().__init__(f"'simulation' was provided but action_status={action_status!r} is not 'simulated'.")


class SimulationControlMismatchError(Exception):
    def __init__(self, control_id: str):
        super().__init__(f"The simulation must include the recommended control ({control_id!r}) among its changed controls.")


class SimulationDateMismatchError(Exception):
    def __init__(self, expected: str, actual: str):
        super().__init__(f"simulation.as_of_date ({actual}) must match the recommendation's as_of_date ({expected}).")


def _parse_intervention_id(state: AppState, merchant_id: str, intervention_id: str) -> tuple[str, date]:
    parts = intervention_id.split(":")
    if len(parts) != 3:
        raise InvalidInterventionIdError(intervention_id, "expected exactly 3 ':'-separated parts: merchant_id:control_id:as_of_date")

    id_merchant_id, control_id, as_of_date_str = parts
    if id_merchant_id != merchant_id:
        raise InvalidInterventionIdError(intervention_id, f"embedded merchant_id {id_merchant_id!r} does not match {merchant_id!r}")
    if control_id not in RULES:
        raise InvalidInterventionIdError(intervention_id, f"unknown control_id {control_id!r} — expected one of {list(RULES)}")
    try:
        as_of_date = date.fromisoformat(as_of_date_str)
    except ValueError as exc:
        raise InvalidInterventionIdError(intervention_id, f"invalid as_of_date {as_of_date_str!r}") from exc

    require_merchant(state.merchants, merchant_id)
    resolve_day_index(state.daily_observations, merchant_id, as_of_date)  # raises DateNotAvailableError if invalid

    return control_id, as_of_date


def record_intervention(
    state: AppState,
    merchant_id: str,
    intervention_id: str,
    action_status: str,
    simulation_request=None,
) -> dict:
    control_id, as_of_date = _parse_intervention_id(state, merchant_id, intervention_id)

    if action_status == "simulated" and simulation_request is None:
        raise SimulationRequiredError()
    if action_status != "simulated" and simulation_request is not None:
        raise SimulationNotApplicableError(action_status)

    simulated_impact = None
    if simulation_request is not None:
        if simulation_request.as_of_date.isoformat() != as_of_date.isoformat():
            raise SimulationDateMismatchError(as_of_date.isoformat(), simulation_request.as_of_date.isoformat())
        interventions = simulation_request.to_interventions()
        if control_id not in interventions:
            raise SimulationControlMismatchError(control_id)

        # Re-runs the REAL simulator — never trusts a client-supplied
        # computed result. Same pattern already established in
        # backend/ai/context_builder.py for the assistant's simulation context.
        result = simulation_service.simulate(
            state, merchant_id, simulation_request.as_of_date, simulation_request.horizon_days, interventions
        )
        simulated_impact = {
            "current_probability": result["current"]["probability_calibrated"],
            "simulated_probability": result["simulated"]["probability_calibrated"],
            "probability_delta_absolute": result["probability_delta"]["absolute"],
            "exposure_current": result["exposure"]["current"]["value"],
            "exposure_simulated": result["exposure"]["simulated"]["value"],
            "liquidity_stress_current": result["liquidity_stress"]["current"]["value"],
            "liquidity_stress_simulated": result["liquidity_stress"]["simulated"]["value"],
            "disclaimer": result["modeled_impact_disclaimer"],
            "provenance": "modeled",
        }

    record = {
        "intervention_id": intervention_id,
        "merchant_id": merchant_id,
        "control_id": control_id,
        "recommendation_title": RULES[control_id].title,
        "action_status": action_status,
        "timestamp": datetime.now(timezone.utc),
        "simulated_impact": simulated_impact,
        "outcome_status": "not_observed",
        "outcome_note": OUTCOME_NOTE,
    }

    state.memory_store.setdefault(merchant_id, []).append(record)
    return record


def list_memory(state: AppState, merchant_id: str) -> dict:
    require_merchant(state.merchants, merchant_id)
    records = state.memory_store.get(merchant_id, [])
    return {
        "merchant_id": merchant_id,
        "count": len(records),
        "records": records,
        "empty_state_note": None if records else EMPTY_MEMORY_NOTE,
    }
