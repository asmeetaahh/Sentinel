"""
Per-archetype modeling assumptions.

All ranges below are synthetic modeling assumptions chosen for plausibility
and internal contrast between archetypes (e.g. SaaS has near-zero refunds,
D2C Fashion has high return rates). They are NOT calibrated to any real
Razorpay or industry dataset. See docs/data_generation.md.

Each range is a (low, high) tuple used to draw a per-merchant baseline value
uniformly (or log-uniformly, where noted) at merchant-creation time. Once
drawn, that value is a fixed property of the merchant for the whole run.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ARCHETYPES, PAYMENT_METHODS


@dataclass(frozen=True)
class ArchetypeParams:
    # Scale (log-uniform draw), currency units are an unspecified synthetic
    # unit — treat as an abstract "GMV unit", not INR/USD.
    daily_gmv_range: tuple  # per business_tier multiplier applied on top
    aov_range: tuple
    refund_rate_range: tuple  # fraction of transactions refunded
    chargeback_rate_range: tuple  # fraction of transactions charged back
    fulfillment_delay_days_range: tuple
    on_time_rate_range: tuple
    new_customer_rate_range: tuple
    payment_mix_weights: dict  # baseline shares over PAYMENT_METHODS, sum ~1
    weekly_profile: tuple  # 7 multipliers, Mon..Sun, mean-normalized to 1.0
    annual_growth_rate_range: tuple  # organic drift, annualized
    volatility_range: tuple  # day-to-day multiplicative noise std
    liquidity_buffer_days_range: tuple
    settlement_cycle_days_range: tuple  # int-ish range
    seasonal_weights: dict  # window name -> participation weight [0,1]


def _norm_weekly(values):
    values = tuple(values)
    mean = sum(values) / len(values)
    return tuple(v / mean for v in values)


ARCHETYPE_PARAMS: dict[str, ArchetypeParams] = {
    "D2C Fashion": ArchetypeParams(
        daily_gmv_range=(8_000, 30_000),
        aov_range=(900, 2200),
        refund_rate_range=(0.06, 0.16),
        chargeback_rate_range=(0.003, 0.012),
        fulfillment_delay_days_range=(2.0, 5.0),
        on_time_rate_range=(0.80, 0.94),
        new_customer_rate_range=(0.35, 0.60),
        payment_mix_weights={"card": 0.32, "upi": 0.38, "netbanking": 0.08, "wallet": 0.12, "bnpl": 0.10},
        weekly_profile=_norm_weekly([0.90, 0.90, 0.95, 1.00, 1.05, 1.15, 1.10]),
        annual_growth_rate_range=(-0.05, 0.45),
        volatility_range=(0.10, 0.22),
        liquidity_buffer_days_range=(3, 10),
        settlement_cycle_days_range=(2, 4),
        seasonal_weights={"festive_autumn": 1.0, "new_year_sales": 0.5, "summer_travel": 0.05, "edu_admission": 0.02, "monsoon_dip": 0.1},
    ),
    "Electronics": ArchetypeParams(
        daily_gmv_range=(15_000, 60_000),
        aov_range=(2500, 9000),
        refund_rate_range=(0.03, 0.09),
        chargeback_rate_range=(0.004, 0.016),
        fulfillment_delay_days_range=(1.5, 4.0),
        on_time_rate_range=(0.82, 0.95),
        new_customer_rate_range=(0.25, 0.50),
        payment_mix_weights={"card": 0.40, "upi": 0.30, "netbanking": 0.10, "wallet": 0.08, "bnpl": 0.12},
        weekly_profile=_norm_weekly([0.95, 0.95, 0.97, 1.00, 1.03, 1.10, 1.08]),
        annual_growth_rate_range=(-0.05, 0.35),
        volatility_range=(0.10, 0.20),
        liquidity_buffer_days_range=(4, 12),
        settlement_cycle_days_range=(2, 5),
        seasonal_weights={"festive_autumn": 0.9, "new_year_sales": 0.8, "summer_travel": 0.05, "edu_admission": 0.02, "monsoon_dip": 0.05},
    ),
    "SaaS": ArchetypeParams(
        daily_gmv_range=(5_000, 25_000),
        aov_range=(1500, 6000),
        refund_rate_range=(0.005, 0.03),
        chargeback_rate_range=(0.001, 0.006),
        fulfillment_delay_days_range=(0.0, 0.2),
        on_time_rate_range=(0.96, 0.999),
        new_customer_rate_range=(0.08, 0.25),
        payment_mix_weights={"card": 0.55, "upi": 0.20, "netbanking": 0.15, "wallet": 0.05, "bnpl": 0.05},
        weekly_profile=_norm_weekly([1.10, 1.10, 1.10, 1.05, 1.00, 0.75, 0.70]),
        annual_growth_rate_range=(0.05, 0.55),
        volatility_range=(0.05, 0.12),
        liquidity_buffer_days_range=(8, 25),
        settlement_cycle_days_range=(1, 3),
        seasonal_weights={"festive_autumn": 0.05, "new_year_sales": 0.15, "summer_travel": 0.02, "edu_admission": 0.05, "monsoon_dip": 0.0},
    ),
    "Travel": ArchetypeParams(
        daily_gmv_range=(10_000, 50_000),
        aov_range=(3000, 15000),
        refund_rate_range=(0.05, 0.14),
        chargeback_rate_range=(0.005, 0.018),
        fulfillment_delay_days_range=(0.0, 1.0),
        on_time_rate_range=(0.85, 0.97),
        new_customer_rate_range=(0.20, 0.45),
        payment_mix_weights={"card": 0.45, "upi": 0.20, "netbanking": 0.12, "wallet": 0.05, "bnpl": 0.18},
        weekly_profile=_norm_weekly([0.90, 0.90, 0.95, 1.00, 1.10, 1.20, 1.15]),
        annual_growth_rate_range=(-0.05, 0.30),
        volatility_range=(0.12, 0.25),
        liquidity_buffer_days_range=(5, 15),
        settlement_cycle_days_range=(3, 7),
        seasonal_weights={"festive_autumn": 0.4, "new_year_sales": 0.15, "summer_travel": 1.0, "edu_admission": 0.02, "monsoon_dip": 0.2},
    ),
    "Marketplace": ArchetypeParams(
        daily_gmv_range=(20_000, 80_000),
        aov_range=(800, 3000),
        refund_rate_range=(0.04, 0.11),
        chargeback_rate_range=(0.003, 0.014),
        fulfillment_delay_days_range=(1.5, 4.5),
        on_time_rate_range=(0.80, 0.93),
        new_customer_rate_range=(0.20, 0.45),
        payment_mix_weights={"card": 0.28, "upi": 0.40, "netbanking": 0.10, "wallet": 0.12, "bnpl": 0.10},
        weekly_profile=_norm_weekly([0.95, 0.97, 1.00, 1.00, 1.02, 1.05, 1.03]),
        annual_growth_rate_range=(0.0, 0.40),
        volatility_range=(0.10, 0.20),
        liquidity_buffer_days_range=(4, 12),
        settlement_cycle_days_range=(2, 6),
        seasonal_weights={"festive_autumn": 0.8, "new_year_sales": 0.5, "summer_travel": 0.05, "edu_admission": 0.02, "monsoon_dip": 0.08},
    ),
    "Education": ArchetypeParams(
        # Revised 2026-08 (see docs/architecture/data_generation.md "Revision
        # history"): the original (4_000, 20_000) / (1200, 8000) combination,
        # crossed with the shared small-tier 0.55x multiplier, could put a
        # merchant's AOV *above* its entire daily GMV target — producing
        # ~1 transaction/day and making chargeback-count outcomes
        # essentially unobservable regardless of injected risk severity.
        # Monte Carlo across the full (gmv, aov, tier) sampling distribution
        # showed this was not a rare tail case: median simulated txn/day was
        # 1.71, with 73% of draws below 3/day. The floor is raised and the
        # AOV ceiling is cut so the archetype now reads as higher-frequency,
        # smaller-ticket recurring purchases (course modules / session fees)
        # rather than infrequent large one-off certifications — a narrower
        # but still plausible characterization, not a real-world statistic.
        # Re-run Monte Carlo: median ~10 txn/day, only ~1% of draws below
        # 3/day. chargeback_rate_range and refund_rate_range are UNCHANGED —
        # this fixes transaction volume only, not risk level.
        daily_gmv_range=(9_000, 25_000),
        aov_range=(500, 2_000),
        refund_rate_range=(0.02, 0.08),
        chargeback_rate_range=(0.001, 0.006),
        fulfillment_delay_days_range=(0.0, 0.5),
        on_time_rate_range=(0.90, 0.99),
        new_customer_rate_range=(0.15, 0.40),
        payment_mix_weights={"card": 0.35, "upi": 0.30, "netbanking": 0.20, "wallet": 0.05, "bnpl": 0.10},
        weekly_profile=_norm_weekly([1.10, 1.10, 1.08, 1.05, 1.00, 0.70, 0.65]),
        annual_growth_rate_range=(0.0, 0.35),
        volatility_range=(0.08, 0.18),
        liquidity_buffer_days_range=(6, 18),
        settlement_cycle_days_range=(2, 5),
        seasonal_weights={"festive_autumn": 0.1, "new_year_sales": 0.05, "summer_travel": 0.0, "edu_admission": 1.0, "monsoon_dip": 0.0},
    ),
    "Quick Commerce": ArchetypeParams(
        daily_gmv_range=(10_000, 45_000),
        aov_range=(300, 900),
        refund_rate_range=(0.02, 0.07),
        chargeback_rate_range=(0.002, 0.010),
        fulfillment_delay_days_range=(0.0, 0.5),
        on_time_rate_range=(0.88, 0.98),
        new_customer_rate_range=(0.30, 0.55),
        payment_mix_weights={"card": 0.15, "upi": 0.55, "netbanking": 0.05, "wallet": 0.20, "bnpl": 0.05},
        weekly_profile=_norm_weekly([0.92, 0.92, 0.95, 1.00, 1.05, 1.20, 1.18]),
        annual_growth_rate_range=(0.05, 0.60),
        volatility_range=(0.12, 0.24),
        liquidity_buffer_days_range=(2, 8),
        settlement_cycle_days_range=(1, 3),
        seasonal_weights={"festive_autumn": 0.5, "new_year_sales": 0.2, "summer_travel": 0.02, "edu_admission": 0.0, "monsoon_dip": 0.25},
    ),
    "Digital Goods": ArchetypeParams(
        daily_gmv_range=(6_000, 28_000),
        aov_range=(300, 2500),
        refund_rate_range=(0.01, 0.05),
        chargeback_rate_range=(0.002, 0.009),
        fulfillment_delay_days_range=(0.0, 0.1),
        on_time_rate_range=(0.97, 0.999),
        new_customer_rate_range=(0.25, 0.50),
        payment_mix_weights={"card": 0.35, "upi": 0.30, "netbanking": 0.05, "wallet": 0.20, "bnpl": 0.10},
        weekly_profile=_norm_weekly([0.95, 0.95, 0.97, 1.00, 1.03, 1.10, 1.08]),
        annual_growth_rate_range=(0.0, 0.45),
        volatility_range=(0.10, 0.20),
        liquidity_buffer_days_range=(5, 15),
        settlement_cycle_days_range=(1, 3),
        seasonal_weights={"festive_autumn": 0.3, "new_year_sales": 0.7, "summer_travel": 0.02, "edu_admission": 0.02, "monsoon_dip": 0.0},
    ),
}

assert set(ARCHETYPE_PARAMS.keys()) == set(ARCHETYPES)
for _name, _params in ARCHETYPE_PARAMS.items():
    assert set(_params.payment_mix_weights.keys()) == set(PAYMENT_METHODS), _name

BUSINESS_TIER_GMV_MULTIPLIER = {"small": 0.55, "mid": 1.0, "large": 2.1}

# ---------------------------------------------------------------------------
# Annual seasonality windows.
#
# Modeled as smooth Gaussian "bumps" over day-of-year (not hard cutoffs), so
# seasonality itself never looks like a sudden single-day spike.
# center_doy: circular day-of-year center (1-365).
# width_days: bump width (std dev of the Gaussian kernel).
# peak_boost: multiplier contribution AT the center for an archetype with
#             seasonal_weights[name] == 1.0 (contribution scales linearly
#             with the archetype's weight below that).
# ---------------------------------------------------------------------------

SEASONAL_WINDOWS = {
    "festive_autumn": {"center_doy": 300, "width_days": 25, "peak_boost": 1.0},
    "new_year_sales": {"center_doy": 5, "width_days": 10, "peak_boost": 0.6},
    "summer_travel": {"center_doy": 140, "width_days": 35, "peak_boost": 0.7},
    "edu_admission": {"center_doy": 15, "width_days": 15, "peak_boost": 0.5},
    "monsoon_dip": {"center_doy": 190, "width_days": 30, "peak_boost": -0.15},
}
