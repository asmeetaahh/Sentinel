"""
Merchant static/attribute table generation.

All draws here happen exactly once per merchant, before any daily simulation
runs, and use only a per-merchant RNG stream keyed by (seed, merchant_idx).
They do not depend on n_days, which keeps the whole run truncation-invariant
(see events.py and generator.py for how that invariance is preserved
end-to-end).
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .archetypes import ARCHETYPE_PARAMS, BUSINESS_TIER_GMV_MULTIPLIER
from .config import (
    ARCHETYPES,
    BUSINESS_TIERS,
    BUSINESS_TIER_WEIGHTS,
    PAYMENT_METHODS,
    RNG_PURPOSE_MERCHANT_STATIC,
)


def _merchant_rng(seed: int, merchant_idx: int) -> np.random.Generator:
    return np.random.default_rng(
        np.random.SeedSequence([seed, RNG_PURPOSE_MERCHANT_STATIC, merchant_idx])
    )


def allocate_archetypes(n_merchants: int) -> list[str]:
    """Deterministic, near-equal allocation of merchants across archetypes.

    Not randomized: for a fixed n_merchants this allocation is identical
    across seeds, which keeps archetype coverage guaranteed regardless of
    RNG choices (important for small benchmark sizes like 50 merchants
    across 8 archetypes).
    """
    n = len(ARCHETYPES)
    base, remainder = divmod(n_merchants, n)
    counts = [base] * n
    for i in range(remainder):
        counts[i] += 1
    allocation: list[str] = []
    for archetype, count in zip(ARCHETYPES, counts):
        allocation.extend([archetype] * count)
    return allocation


def _weekly_profile_tag(profile: tuple[float, ...]) -> str:
    weekday_mean = sum(profile[0:5]) / 5
    weekend_mean = sum(profile[5:7]) / 2
    if weekend_mean > weekday_mean * 1.05:
        return "weekend_heavy"
    if weekday_mean > weekend_mean * 1.05:
        return "weekday_heavy"
    return "flat"


def generate_merchants(
    seed: int,
    n_merchants: int,
    start_date: date,
) -> pd.DataFrame:
    archetype_allocation = allocate_archetypes(n_merchants)

    rows = []
    for idx, archetype in enumerate(archetype_allocation):
        merchant_id = f"M{idx:04d}"
        rng = _merchant_rng(seed, idx)
        params = ARCHETYPE_PARAMS[archetype]

        business_tier = rng.choice(BUSINESS_TIERS, p=BUSINESS_TIER_WEIGHTS)
        tier_mult = BUSINESS_TIER_GMV_MULTIPLIER[business_tier]

        # Log-uniform draw within the archetype's GMV range keeps the
        # merchant-scale distribution right-skewed (a few large merchants,
        # many small ones), which is closer to real marketplace behavior
        # than a uniform draw.
        gmv_lo, gmv_hi = params.daily_gmv_range
        log_gmv = rng.uniform(np.log(gmv_lo), np.log(gmv_hi))
        baseline_daily_gmv = float(np.exp(log_gmv)) * tier_mult

        aov_lo, aov_hi = params.aov_range
        baseline_aov = float(rng.uniform(aov_lo, aov_hi))
        baseline_daily_txn_count = max(1.0, baseline_daily_gmv / baseline_aov)

        baseline_refund_rate = float(rng.uniform(*params.refund_rate_range))
        baseline_chargeback_rate = float(rng.uniform(*params.chargeback_rate_range))
        baseline_fulfillment_delay_days = float(rng.uniform(*params.fulfillment_delay_days_range))
        baseline_on_time_rate = float(rng.uniform(*params.on_time_rate_range))
        baseline_new_customer_rate = float(rng.uniform(*params.new_customer_rate_range))

        # Payment mix: perturb archetype baseline weights with small
        # per-merchant Dirichlet-like noise, then renormalize to sum to 1.
        base_weights = np.array([params.payment_mix_weights[m] for m in PAYMENT_METHODS])
        noisy_weights = np.clip(base_weights * rng.uniform(0.85, 1.15, size=len(PAYMENT_METHODS)), 1e-4, None)
        noisy_weights = noisy_weights / noisy_weights.sum()

        annual_growth_rate = float(rng.uniform(*params.annual_growth_rate_range))
        volatility_factor = float(rng.uniform(*params.volatility_range))
        liquidity_buffer_days = float(rng.uniform(*params.liquidity_buffer_days_range))
        settlement_cycle_days = int(rng.integers(params.settlement_cycle_days_range[0], params.settlement_cycle_days_range[1] + 1))

        # Tenure: signup happened well before the observation window so
        # every merchant has full history within the run (no cold-start
        # partial-history handling needed at this stage).
        tenure_days = int(rng.integers(60, 1500))
        signup_date = start_date - timedelta(days=tenure_days)

        row = {
            "merchant_id": merchant_id,
            "archetype": archetype,
            "business_tier": business_tier,
            "signup_date": signup_date,
            "baseline_daily_gmv": baseline_daily_gmv,
            "baseline_daily_txn_count": baseline_daily_txn_count,
            "baseline_aov": baseline_aov,
            "baseline_refund_rate": baseline_refund_rate,
            "baseline_chargeback_rate": baseline_chargeback_rate,
            "baseline_fulfillment_delay_days": baseline_fulfillment_delay_days,
            "baseline_on_time_rate": baseline_on_time_rate,
            "baseline_new_customer_rate": baseline_new_customer_rate,
            "annual_growth_rate": annual_growth_rate,
            "volatility_factor": volatility_factor,
            "liquidity_buffer_days": liquidity_buffer_days,
            "settlement_cycle_days": settlement_cycle_days,
            "weekly_seasonality_profile": _weekly_profile_tag(params.weekly_profile),
        }
        for method, weight in zip(PAYMENT_METHODS, noisy_weights):
            row[f"baseline_pct_pay_{method}"] = float(weight)

        rows.append(row)

    df = pd.DataFrame(rows)
    from .schema import columns

    return df[columns("merchants")]
