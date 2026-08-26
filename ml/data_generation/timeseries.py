"""
Daily observation simulation.

For a fixed merchant, days are simulated strictly sequentially, day_index
0..n_days-1, using ONE per-merchant RNG stream (config.RNG_PURPOSE_DAILY)
consumed in a fixed, unconditional draw order every day. Because the draw
order and count per day never depends on n_days (only on the day itself and
prior state, e.g. yesterday's liquidity_balance), day t's output is a pure
function of (seed, merchant_idx, day 0..t) and is therefore identical
whether the run generates 90 days or 365 days — the property directly
exercised by the truncation-invariance / no-look-ahead tests.

All financial/count quantities are clipped to be non-negative before
being written out.
"""

from __future__ import annotations

from collections import deque
from datetime import date, timedelta

import numpy as np

from .archetypes import ARCHETYPE_PARAMS, SEASONAL_WINDOWS
from .config import PAYMENT_METHODS, RNG_PURPOSE_DAILY
from .events import EventInstance, active_events_for_day, combine_event_effects


def _circular_doy_distance(doy: float, center: float) -> float:
    diff = abs(doy - center) % 365
    return min(diff, 365 - diff)


def annual_seasonal_multiplier(archetype: str, doy: int) -> float:
    params = ARCHETYPE_PARAMS[archetype]
    total = 1.0
    for name, window in SEASONAL_WINDOWS.items():
        weight = params.seasonal_weights.get(name, 0.0)
        if weight == 0.0:
            continue
        dist = _circular_doy_distance(doy, window["center_doy"])
        bump = np.exp(-0.5 * (dist / window["width_days"]) ** 2)
        total += weight * window["peak_boost"] * bump
    return float(np.clip(total, 0.3, 3.5))


def _weekly_multiplier(archetype: str, weekday: int) -> float:
    return ARCHETYPE_PARAMS[archetype].weekly_profile[weekday]


def simulate_merchant_days(
    seed: int,
    merchant_idx: int,
    merchant: dict,
    n_days: int,
    start_date: date,
    events: list[EventInstance],
) -> list[dict]:
    archetype = merchant["archetype"]
    rng = np.random.default_rng(np.random.SeedSequence([seed, RNG_PURPOSE_DAILY, merchant_idx]))

    base_payment_weights = np.array([merchant[f"baseline_pct_pay_{m}"] for m in PAYMENT_METHODS])
    n_methods = len(PAYMENT_METHODS)

    liquidity_balance = merchant["liquidity_buffer_days"] * merchant["baseline_daily_gmv"]
    settlement_cycle_days = int(merchant["settlement_cycle_days"])
    net_amount_window: deque[float] = deque(maxlen=settlement_cycle_days)

    rows: list[dict] = []

    for day_index in range(n_days):
        d = start_date + timedelta(days=day_index)
        weekday = d.weekday()
        doy = d.timetuple().tm_yday

        trend_mult = (1.0 + merchant["annual_growth_rate"]) ** (day_index / 365.0)
        weekly_mult = _weekly_multiplier(archetype, weekday)
        seasonal_mult = annual_seasonal_multiplier(archetype, doy)

        active = active_events_for_day(events, day_index)
        effects = combine_event_effects(active, day_index, n_methods)

        volatility = merchant["volatility_factor"]

        target_gmv = (
            merchant["baseline_daily_gmv"]
            * trend_mult
            * weekly_mult
            * seasonal_mult
            * effects["gmv_mult"]
        )
        gmv_noise_mult = float(np.exp(rng.normal(0.0, volatility)))
        gmv = max(target_gmv * gmv_noise_mult, 1.0)

        aov_noise_mult = float(np.exp(rng.normal(0.0, volatility * 0.4)))
        aov_target = max(merchant["baseline_aov"] * aov_noise_mult, 1.0)

        transaction_count = max(1, int(round(gmv / aov_target)))
        aov = gmv / transaction_count

        refund_rate_noise = float(np.exp(rng.normal(0.0, 0.15)))
        effective_refund_rate = float(
            np.clip(merchant["baseline_refund_rate"] * effects["refund_rate_mult"] * refund_rate_noise, 0.0, 0.9)
        )
        refund_count = int(min(transaction_count, rng.poisson(transaction_count * effective_refund_rate)))
        refund_ticket_factor = float(np.clip(rng.normal(0.95, 0.08), 0.4, 1.2))
        refund_amount = min(refund_count * aov * refund_ticket_factor, gmv)
        refund_amount = max(refund_amount, 0.0)

        chargeback_rate_noise = float(np.exp(rng.normal(0.0, 0.20)))
        effective_chargeback_rate = float(
            np.clip(merchant["baseline_chargeback_rate"] * effects["chargeback_rate_mult"] * chargeback_rate_noise, 0.0, 0.5)
        )
        chargeback_count = int(min(transaction_count, rng.poisson(transaction_count * effective_chargeback_rate)))
        chargeback_ticket_factor = float(np.clip(rng.normal(1.0, 0.10), 0.5, 1.5))
        chargeback_amount = max(chargeback_count * aov * chargeback_ticket_factor, 0.0)

        fulfillment_delay_avg_days = max(
            0.0,
            merchant["baseline_fulfillment_delay_days"] + effects["delay_add_days"] + rng.normal(0.0, 0.3),
        )
        fulfillment_on_time_rate = float(
            np.clip(
                merchant["baseline_on_time_rate"] + effects["on_time_rate_delta"] + rng.normal(0.0, 0.02),
                0.01,
                0.999,
            )
        )

        new_customer_rate_noise = float(np.exp(rng.normal(0.0, 0.10)))
        effective_new_customer_rate = float(
            np.clip(merchant["baseline_new_customer_rate"] * effects["new_customer_rate_mult"] * new_customer_rate_noise, 0.01, 0.98)
        )
        customer_count = transaction_count
        new_customers = int(np.clip(round(customer_count * effective_new_customer_rate), 0, customer_count))
        returning_customers = customer_count - new_customers
        new_customer_rate_out = new_customers / customer_count if customer_count > 0 else 0.0

        payment_mix = base_payment_weights + effects["payment_mix_delta"] + rng.normal(0.0, 0.01, size=n_methods)
        payment_mix = np.clip(payment_mix, 1e-4, None)
        payment_mix = payment_mix / payment_mix.sum()

        net_amount_window.append(gmv - refund_amount)
        pending_settlement_amount = max(0.0, float(sum(net_amount_window)))

        target_liquidity = merchant["liquidity_buffer_days"] * gmv
        phi = 0.90
        liquidity_balance = (
            phi * liquidity_balance
            + (1 - phi) * target_liquidity
            - refund_amount * 0.05
            - chargeback_amount * 0.15
            + rng.normal(0.0, target_liquidity * 0.01 + 1.0)
        )
        liquidity_balance = max(0.0, liquidity_balance)

        row = {
            "merchant_id": merchant["merchant_id"],
            "date": d,
            "day_index": day_index,
            "gmv": gmv,
            "transaction_count": transaction_count,
            "aov": aov,
            "refund_count": refund_count,
            "refund_amount": refund_amount,
            "refund_rate": refund_count / transaction_count,
            "chargeback_count": chargeback_count,
            "chargeback_amount": chargeback_amount,
            "chargeback_rate": chargeback_count / transaction_count,
            "fulfillment_delay_avg_days": fulfillment_delay_avg_days,
            "fulfillment_on_time_rate": fulfillment_on_time_rate,
            "customer_count": customer_count,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
            "new_customer_rate": new_customer_rate_out,
            "liquidity_balance": liquidity_balance,
            "pending_settlement_amount": pending_settlement_amount,
        }
        for method, share in zip(PAYMENT_METHODS, payment_mix):
            row[f"pct_pay_{method}"] = float(share)

        rows.append(row)

    return rows
