"""
Intervention Intelligence's rule registry — the ONLY place that decides
whether a bounded simulator control is a "meaningful intervention
candidate" for a merchant's current state. See
docs/architecture/intervention_intelligence.md for the full rationale.

This module does NOT redefine the simulator's controls. It references
them by control_id from backend/simulation/controls.py (the single source
of truth for control_id/feature/label/group/bounds) and adds only the
intervention-specific metadata: which existing deviation-from-baseline
feature to check, which direction is "worse," and the merchant-facing
title. It is deliberately impossible for these rules to drift from the
simulator's own control definitions, because they never re-declare them.

Relevance signal: ml/features' own "deviation from merchant-specific
baseline" feature group (docs/architecture/feature_engineering.md group 9)
— a z-score of the merchant's own recent (7d) value against its own
expanding-history mean/std of a 28d-smoothed series, already computed by
the existing, unmodified feature pipeline. This is the correct existing
signal for "has this metric shifted materially from what's normal for
THIS merchant" — nothing here computes a new statistic.

RELEVANCE_Z_THRESHOLD = 2.0 was chosen by inspecting the real distribution
of these three deviation-z features across the full 50x180 benchmark
(9,000 merchant-days), not tuned to hit a target recommendation count —
the directional "bad" fraction of rows crossing this threshold:

    refund_rate_deviation_z >= 2.0:               16.8% of rows
    fulfillment_on_time_rate_deviation_z <= -2.0:  19.4% of rows
    new_customer_rate_deviation_z >= 2.0:          18.2% of rows

(roughly the most-deviated sixth-to-fifth of observations in the "bad"
direction for each control — see docs/architecture/intervention_intelligence.md
for the exact reproduction commands). On the latest observed day per
merchant, this threshold yields 0 relevant controls for 35 of 50
merchants, 1 for 11, and 2 for 4 (0 merchants had all 3 on that specific
day) — a genuinely selective bar, not "show every control to everyone."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["high_is_bad", "low_is_bad"]

RELEVANCE_Z_THRESHOLD = 2.0


@dataclass(frozen=True)
class InterventionRule:
    control_id: str
    deviation_feature: str
    direction: Direction
    title: str
    metric_label: str


# Fixed iteration/tie-break order — also the CONTROLS dict's own order
# (backend/simulation/controls.py) — never re-sorted based on any
# per-request computation, so ties are always broken the same way.
RULES: dict[str, InterventionRule] = {
    "refund_rate_28d": InterventionRule(
        control_id="refund_rate_28d",
        deviation_feature="refund_rate_deviation_z",
        direction="high_is_bad",
        title="Review refund pressure",
        metric_label="Refund rate (trailing 28 days)",
    ),
    "fulfillment_on_time_rate_28d": InterventionRule(
        control_id="fulfillment_on_time_rate_28d",
        deviation_feature="fulfillment_on_time_rate_deviation_z",
        direction="low_is_bad",
        title="Review fulfillment reliability",
        metric_label="On-time fulfillment rate (trailing 28 days)",
    ),
    "new_customer_rate_28d": InterventionRule(
        control_id="new_customer_rate_28d",
        deviation_feature="new_customer_rate_deviation_z",
        direction="high_is_bad",
        title="Review customer-mix shift",
        metric_label="New-customer share (trailing 28 days)",
    ),
}


def signed_badness(rule: InterventionRule, deviation_z: float) -> float:
    """A single signed scale where LARGER is always MORE concerning,
    regardless of the rule's direction — the one quantity relevance and
    ranking are both computed from.
    """
    return deviation_z if rule.direction == "high_is_bad" else -deviation_z


def is_relevant(rule: InterventionRule, deviation_z: float) -> bool:
    return signed_badness(rule, deviation_z) >= RELEVANCE_Z_THRESHOLD
