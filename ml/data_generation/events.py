"""
Event/scenario scheduling and per-day effect computation.

Design invariant (critical — see tests/test_data_generation.py):
Event candidates for a merchant are drawn from a single sequential RNG
stream keyed only by (seed, merchant_idx), using a FIXED stopping bound
(config.EVENT_SCHEDULE_HORIZON_DAYS) that does not depend on the requested
n_days. A run with n_days=90 therefore sees a strict prefix of the same
candidate list a run with n_days=365 would see, filtered to
start_day < n_days. This is what makes "generate fewer days" never change
the events (or any downstream daily values) for the days that do get
generated — the direct, testable definition of "no look-ahead" for this
module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from .config import (
    EVENT_GRADUAL_PROBABILITY,
    EVENT_MEAN_GAP_DAYS,
    EVENT_SCHEDULE_HORIZON_DAYS,
    EVENT_TYPES,
    EVENT_TYPE_WEIGHTS,
    EVENT_CATEGORY_BENIGN_GROWTH,
    RNG_PURPOSE_EVENT_SCHEDULE,
)

_EVENT_TYPE_LIST = list(EVENT_TYPES.keys())
_EVENT_TYPE_PROBS = np.array([EVENT_TYPE_WEIGHTS[t] for t in _EVENT_TYPE_LIST])
_EVENT_TYPE_PROBS = _EVENT_TYPE_PROBS / _EVENT_TYPE_PROBS.sum()

# (duration_low, duration_high, recovery_low, recovery_high) in days, per type.
_DURATION_RECOVERY = {
    "chargeback_deterioration": (20, 45, 10, 20),
    "refund_shock": (5, 20, 5, 12),
    "fulfillment_degradation": (15, 40, 8, 18),
    "customer_mix_shift": (20, 40, 10, 20),
    "compound_risk": (25, 50, 12, 20),
    "festival_growth": (7, 21, 3, 8),
    "viral_campaign": (5, 15, 3, 8),
    "product_launch": (30, 60, 5, 15),
    "payment_method_shift": (30, 60, 5, 12),
}

# Human-readable metric groups touched per event type, for the events table.
AFFECTS = {
    "chargeback_deterioration": "chargeback_rate",
    "refund_shock": "refund_rate",
    "fulfillment_degradation": "fulfillment_on_time_rate,fulfillment_delay_avg_days,chargeback_rate",
    "customer_mix_shift": "new_customer_rate,chargeback_rate",
    "compound_risk": "refund_rate,chargeback_rate,fulfillment_on_time_rate",
    "festival_growth": "gmv,transaction_count",
    "viral_campaign": "gmv,transaction_count,new_customer_rate",
    "product_launch": "gmv,transaction_count,new_customer_rate",
    "payment_method_shift": "payment_mix,gmv",
}


@dataclass
class EventInstance:
    event_id: str
    merchant_id: str
    event_type: str
    category: str
    hard_negative: bool
    shape: str
    start_day: int
    duration_days: int
    recovery_days: int
    severity_score: float
    params: dict = field(default_factory=dict)

    @property
    def end_day(self) -> int:
        return self.start_day + self.duration_days

    @property
    def recovery_end_day(self) -> int:
        return self.end_day + self.recovery_days

    def intensity(self, day_index: int) -> float:
        return self.intensity_with_extra_lag(day_index, 0)

    def intensity_with_extra_lag(self, day_index: int, extra_lag_days: float) -> float:
        return get_intensity(
            day_index - self.start_day - extra_lag_days,
            self.duration_days,
            self.recovery_days,
            self.shape,
        )


def get_intensity(day_offset: int, duration_days: int, recovery_days: int, shape: str) -> float:
    """Intensity in [0, 1] for a day relative to an event's start.

    'gradual': smoothstep rise over the first 70% of duration_days, then
    holds at peak until duration_days, then linear decay over recovery_days.
    'sudden': near-immediate rise (first 10% of duration_days), same hold
    and decay tail.
    """
    if day_offset < 0:
        return 0.0
    if day_offset <= duration_days:
        ramp_fraction = 0.10 if shape == "sudden" else 0.70
        ramp_len = max(1.0, duration_days * ramp_fraction)
        r = min(1.0, day_offset / ramp_len)
        return 3 * r**2 - 2 * r**3  # smoothstep — no discontinuity even for 'sudden'
    if recovery_days > 0 and day_offset <= duration_days + recovery_days:
        decay_fraction = (day_offset - duration_days) / recovery_days
        return max(0.0, 1.0 - decay_fraction)
    return 0.0


def _sample_severity_params(rng: np.random.Generator, event_type: str) -> tuple[dict, float]:
    """Returns (params, severity_score in [0,1]) for one event instance."""
    if event_type == "chargeback_deterioration":
        peak = rng.uniform(1.5, 5.0)
        params = {"chargeback_mult_peak": peak}
        score = (peak - 1.5) / (5.0 - 1.5)
    elif event_type == "refund_shock":
        peak = rng.uniform(1.8, 4.0)
        params = {"refund_mult_peak": peak}
        score = (peak - 1.8) / (4.0 - 1.8)
    elif event_type == "fulfillment_degradation":
        on_time_drop = rng.uniform(0.15, 0.5)
        delay_add = rng.uniform(1.0, 6.0)
        linked_cb = rng.uniform(1.1, 1.4)
        params = {"on_time_drop_peak": on_time_drop, "delay_add_peak": delay_add, "linked_chargeback_mult_peak": linked_cb}
        score = (on_time_drop - 0.15) / (0.5 - 0.15)
    elif event_type == "customer_mix_shift":
        new_cust_mult = rng.uniform(1.3, 2.2)
        lag_chargeback_mult = rng.uniform(1.3, 2.0)
        lag_days = int(rng.integers(10, 21))
        params = {"new_customer_mult_peak": new_cust_mult, "lag_chargeback_mult_peak": lag_chargeback_mult, "lag_days": lag_days}
        score = (new_cust_mult - 1.3) / (2.2 - 1.3)
    elif event_type == "compound_risk":
        refund_mult = rng.uniform(1.5, 3.0)
        chargeback_mult = rng.uniform(1.4, 3.5)
        on_time_drop = rng.uniform(0.05, 0.25)
        chargeback_lag_fraction = rng.uniform(0.2, 0.4)
        params = {
            "refund_mult_peak": refund_mult,
            "chargeback_mult_peak": chargeback_mult,
            "on_time_drop_peak": on_time_drop,
            "chargeback_lag_fraction": chargeback_lag_fraction,
        }
        score = (chargeback_mult - 1.4) / (3.5 - 1.4)
    elif event_type == "festival_growth":
        peak = rng.uniform(1.3, 3.0)
        params = {"gmv_mult_peak": peak}
        score = (peak - 1.3) / (3.0 - 1.3)
    elif event_type == "viral_campaign":
        gmv_peak = rng.uniform(1.5, 4.0)
        new_cust_peak = rng.uniform(1.5, 3.0)
        params = {"gmv_mult_peak": gmv_peak, "new_customer_mult_peak": new_cust_peak}
        score = (gmv_peak - 1.5) / (4.0 - 1.5)
    elif event_type == "product_launch":
        gmv_peak = rng.uniform(1.3, 2.5)
        new_cust_peak = rng.uniform(1.3, 2.2)
        params = {"gmv_mult_peak": gmv_peak, "new_customer_mult_peak": new_cust_peak}
        score = (gmv_peak - 1.3) / (2.5 - 1.3)
    elif event_type == "payment_method_shift":
        # gmv_mult_peak is intentionally small and is NOT the scenario's
        # primary signal — this is a payment-mix/operational-transition
        # hard negative first, a mild GMV tailwind second. GMV growth is not
        # guaranteed for any individual instance: ordinary trend/seasonality/
        # noise (volatility_range up to 0.24) routinely dominates a peak
        # multiplier this small. See docs/architecture/data_generation.md.
        shift_magnitude = rng.uniform(0.10, 0.35)
        gmv_peak = rng.uniform(1.02, 1.15)
        from_method_idx = rng.integers(0, 5)
        to_method_idx = rng.integers(0, 5)
        while to_method_idx == from_method_idx:
            # Resample so the scenario always has a real payment-mix effect
            # to observe — a same-method "shift" was a no-op bug: it still
            # recorded a nonzero severity_score and affects=payment_mix,gmv
            # despite zero actual payment-mix change.
            to_method_idx = rng.integers(0, 5)
        params = {
            "shift_magnitude_peak": shift_magnitude,
            "gmv_mult_peak": gmv_peak,
            "from_method_idx": int(from_method_idx),
            "to_method_idx": int(to_method_idx),
        }
        score = (shift_magnitude - 0.10) / (0.35 - 0.10)
    else:  # pragma: no cover - EVENT_TYPES is the exhaustive source of truth
        raise ValueError(f"Unknown event_type: {event_type}")
    return params, float(np.clip(score, 0.0, 1.0))


def _describe(event_type: str, category: str, shape: str) -> str:
    label = "risk" if category != EVENT_CATEGORY_BENIGN_GROWTH else "benign growth (hard negative)"
    return f"{event_type.replace('_', ' ')} ({shape} onset, {label})"


def schedule_events_for_merchant(
    seed: int, merchant_idx: int, merchant_id: str, n_days: int
) -> list[EventInstance]:
    """Schedule this merchant's events, filtered to those starting within
    [0, n_days). Uses a fixed, n_days-independent stopping bound so the
    result for a smaller n_days is always a filtered prefix of the result
    for a larger n_days (see module docstring).
    """
    rng = np.random.default_rng(np.random.SeedSequence([seed, RNG_PURPOSE_EVENT_SCHEDULE, merchant_idx]))

    events: list[EventInstance] = []
    cursor = 0
    slot = 0
    while cursor < EVENT_SCHEDULE_HORIZON_DAYS:
        gap = rng.exponential(EVENT_MEAN_GAP_DAYS)
        # +1 guarantees a whole day of separation even when a very small gap
        # rounds down to the previous event's exact recovery_end_day.
        cursor += gap + 1
        start_day = int(round(cursor))

        event_type = str(rng.choice(_EVENT_TYPE_LIST, p=_EVENT_TYPE_PROBS))
        category = EVENT_TYPES[event_type]
        hard_negative = category == EVENT_CATEGORY_BENIGN_GROWTH
        gradual_prob = EVENT_GRADUAL_PROBABILITY[event_type]
        shape = "gradual" if rng.uniform() < gradual_prob else "sudden"

        dur_lo, dur_hi, rec_lo, rec_hi = _DURATION_RECOVERY[event_type]
        duration_days = int(rng.integers(dur_lo, dur_hi + 1))
        recovery_days = int(rng.integers(rec_lo, rec_hi + 1))
        params, severity_score = _sample_severity_params(rng, event_type)

        if start_day < n_days:
            events.append(
                EventInstance(
                    event_id=f"E{merchant_idx:04d}{slot:03d}",
                    merchant_id=merchant_id,
                    event_type=event_type,
                    category=category,
                    hard_negative=hard_negative,
                    shape=shape,
                    start_day=start_day,
                    duration_days=duration_days,
                    recovery_days=recovery_days,
                    severity_score=severity_score,
                    params=params,
                )
            )
        slot += 1
        # Advance the cursor to this event's recovery_end_day (not just its
        # start_day) so a merchant's own events never overlap each other —
        # overlap would silently contaminate "hard negative" benign_growth
        # windows with a concurrent risk event's rate effects (or vice
        # versa), undermining the very contrast the benchmark exists to
        # test. This still does not depend on n_days, so truncation
        # invariance (see module docstring) is preserved.
        cursor = start_day + duration_days + recovery_days

    return events


def events_to_rows(events: list[EventInstance], start_date: date, n_days: int) -> list[dict]:
    rows = []
    for ev in events:
        clipped_end_day = min(ev.end_day, n_days - 1)
        clipped_recovery_end_day = min(ev.recovery_end_day, n_days - 1)
        rows.append(
            {
                "event_id": ev.event_id,
                "merchant_id": ev.merchant_id,
                "event_type": ev.event_type,
                "category": ev.category,
                "hard_negative": ev.hard_negative,
                "shape": ev.shape,
                "start_date": start_date + timedelta(days=ev.start_day),
                "end_date": start_date + timedelta(days=clipped_end_day),
                "recovery_end_date": start_date + timedelta(days=clipped_recovery_end_day),
                "duration_days": ev.duration_days,
                "severity_score": ev.severity_score,
                "affects": AFFECTS[ev.event_type],
                "description": _describe(ev.event_type, ev.category, ev.shape),
            }
        )
    return rows


def active_events_for_day(events: list[EventInstance], day_index: int) -> list[EventInstance]:
    return [ev for ev in events if ev.start_day <= day_index <= ev.recovery_end_day]


def combine_event_effects(active_events: list[EventInstance], day_index: int, n_methods: int) -> dict:
    """Combine all events active on day_index into one additive/multiplicative
    effect bundle applied to that day's metrics. Multiple simultaneous events
    compound (multiplicatively for rates/gmv, additively for deltas) — this
    is intentional: overlapping benign-growth and risk events are among the
    hardest, most realistic cases in the benchmark.
    """
    gmv_mult = 1.0
    refund_rate_mult = 1.0
    chargeback_rate_mult = 1.0
    on_time_rate_delta = 0.0
    delay_add_days = 0.0
    new_customer_rate_mult = 1.0
    payment_mix_delta = np.zeros(n_methods)

    for ev in active_events:
        i = ev.intensity(day_index)
        if i <= 0:
            continue
        p = ev.params

        if ev.event_type == "chargeback_deterioration":
            chargeback_rate_mult *= 1 + i * (p["chargeback_mult_peak"] - 1)
        elif ev.event_type == "refund_shock":
            refund_rate_mult *= 1 + i * (p["refund_mult_peak"] - 1)
        elif ev.event_type == "fulfillment_degradation":
            on_time_rate_delta -= i * p["on_time_drop_peak"]
            delay_add_days += i * p["delay_add_peak"]
            chargeback_rate_mult *= 1 + i * (p["linked_chargeback_mult_peak"] - 1)
        elif ev.event_type == "customer_mix_shift":
            new_customer_rate_mult *= 1 + i * (p["new_customer_mult_peak"] - 1)
            lag_i = ev.intensity_with_extra_lag(day_index, p["lag_days"])
            chargeback_rate_mult *= 1 + lag_i * (p["lag_chargeback_mult_peak"] - 1)
        elif ev.event_type == "compound_risk":
            refund_rate_mult *= 1 + i * (p["refund_mult_peak"] - 1)
            on_time_rate_delta -= i * p["on_time_drop_peak"]
            lag_days = ev.duration_days * p["chargeback_lag_fraction"]
            lag_i = ev.intensity_with_extra_lag(day_index, lag_days)
            chargeback_rate_mult *= 1 + lag_i * (p["chargeback_mult_peak"] - 1)
        elif ev.event_type in ("festival_growth", "viral_campaign", "product_launch"):
            gmv_mult *= 1 + i * (p["gmv_mult_peak"] - 1)
            if "new_customer_mult_peak" in p:
                new_customer_rate_mult *= 1 + i * (p["new_customer_mult_peak"] - 1)
        elif ev.event_type == "payment_method_shift":
            gmv_mult *= 1 + i * (p["gmv_mult_peak"] - 1)
            shift = i * p["shift_magnitude_peak"]
            payment_mix_delta[p["from_method_idx"]] -= shift
            payment_mix_delta[p["to_method_idx"]] += shift

    return {
        "gmv_mult": gmv_mult,
        "refund_rate_mult": refund_rate_mult,
        "chargeback_rate_mult": chargeback_rate_mult,
        "on_time_rate_delta": on_time_rate_delta,
        "delay_add_days": delay_add_days,
        "new_customer_rate_mult": new_customer_rate_mult,
        "payment_mix_delta": payment_mix_delta,
    }
