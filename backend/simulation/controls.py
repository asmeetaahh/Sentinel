"""
The simulator's control registry: a small, curated set of trailing-28-day
feature columns that can be safely exposed as a bounded "what-if" input.

Why only these three (see docs/architecture/simulator.md for the full
rationale):
    - Each maps to exactly ONE existing feature column from
      ml/features/build_features.py — no new feature is invented, and no
      existing feature is redefined.
    - Each represents an operational metric a merchant could plausibly act
      on going forward (refund handling, fulfillment execution, acquisition
      mix) — not a metric that is itself a near-definition of the outcome
      being predicted (chargeback-rate features were deliberately excluded
      for this reason; editing "your own past chargeback rate" is not an
      operational lever a merchant can pull).
    - The 28-day window was chosen over 7d/60d for every control because
      it is the pipeline's own primary/most-cited window (see
      docs/architecture/feature_engineering.md) and gives the clearest
      single "current sustained level" framing for a what-if slider.

This module intentionally does NOT touch any sibling feature (the 7d/60d
windows of the same metric, its velocity/acceleration/deviation-z
derivatives). Recomputing those consistently would require either
fabricating a full alternate daily history (explicitly forbidden) or
inventing an ad hoc cascading-update rule for which no validated
methodology exists. Leaving them at their observed values, and saying so
explicitly, is the more honest choice — see simulation_service.py and
docs/architecture/simulator.md "Limitations".
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.api.state import AppState


@dataclass(frozen=True)
class SimulatorControl:
    control_id: str
    feature: str
    label: str
    group: str
    unit: str
    description: str


CONTROLS: dict[str, SimulatorControl] = {
    "refund_rate_28d": SimulatorControl(
        control_id="refund_rate_28d",
        feature="refund_rate_28d",
        label="Refund rate (trailing 28 days)",
        group="refund_behavior",
        unit="rate_0_to_1",
        description=(
            "Volume-weighted share of transactions refunded over a trailing 28-day window "
            "(sum(refund_count)/sum(transaction_count)). Maps directly to the refund_rate_28d "
            "feature the saved model was trained on — see docs/architecture/feature_engineering.md."
        ),
    ),
    "fulfillment_on_time_rate_28d": SimulatorControl(
        control_id="fulfillment_on_time_rate_28d",
        feature="fulfillment_on_time_rate_28d",
        label="On-time fulfillment rate (trailing 28 days)",
        group="fulfillment",
        unit="rate_0_to_1",
        description=(
            "Transaction-volume-weighted mean on-time fulfillment rate over a trailing 28-day "
            "window. Maps directly to the fulfillment_on_time_rate_28d feature the saved model "
            "was trained on — see docs/architecture/feature_engineering.md."
        ),
    ),
    "new_customer_rate_28d": SimulatorControl(
        control_id="new_customer_rate_28d",
        feature="new_customer_rate_28d",
        label="New-customer share (trailing 28 days)",
        group="customer_mix",
        unit="rate_0_to_1",
        description=(
            "Volume-weighted share of transactions from new (vs. returning) customers over a "
            "trailing 28-day window (sum(new_customers)/sum(customer_count)). Maps directly to "
            "the new_customer_rate_28d feature the saved model was trained on — see "
            "docs/architecture/feature_engineering.md."
        ),
    ),
}


class UnknownControlError(Exception):
    def __init__(self, control_id: str, known: list[str]):
        self.control_id = control_id
        self.known = known
        super().__init__(f"Unknown simulator control_id: {control_id!r}. Known controls: {known}.")


class ControlOutOfRangeError(Exception):
    def __init__(self, control_id: str, value: float, min_value: float, max_value: float):
        self.control_id = control_id
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(
            f"control_id={control_id!r} value={value} is outside the allowed range "
            f"[{min_value}, {max_value}] (the full observed range of this feature across the "
            "50x180 synthetic benchmark — the simulator refuses to ask the model to extrapolate "
            "beyond values it has ever seen)."
        )


class NoInterventionProvidedError(Exception):
    def __init__(self):
        super().__init__(
            "At least one control must be set to run a simulation "
            f"(known controls: {list(CONTROLS)})."
        )


def control_bounds(state: AppState, control: SimulatorControl) -> tuple[float, float]:
    """The full observed [min, max] of this feature across every merchant
    and day in the loaded benchmark — a data-driven bound, not an arbitrary
    or hardcoded one, and never wider than what the model was ever trained
    or evaluated on.
    """
    series = state.features[control.feature]
    return float(series.min()), float(series.max())
