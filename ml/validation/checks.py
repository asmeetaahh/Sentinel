"""
Exploratory / structural validation checks for the synthetic merchant
benchmark (ml/data_generation). This module performs *diagnosis only* — it
never modifies the generator or the dataset. Every function returns plain,
JSON-serializable Python types (via `_to_native`) so results can be dumped
to data/metadata/validation/summary.json without extra glue.

Design note: several checks here deliberately RECOMPUTE quantities (e.g. a
trailing chargeback rate) from daily_observations rather than reading the
equivalent column out of labels.csv. That is intentional — see
check_leakage_audit — importing anything from the labels table into a
feature-shaped computation is exactly the habit this module warns against
adopting later, so the validation code itself follows the same discipline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml.data_generation import config as cfg
from ml.data_generation.schema import columns as schema_columns
from .stats_utils import auc_from_scores, robust_summary

EPS = 1e-9

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_dataset(data_dir: Path) -> dict[str, pd.DataFrame]:
    data_dir = Path(data_dir)
    merchants = pd.read_csv(data_dir / "raw" / "merchants.csv", parse_dates=["signup_date"])
    daily = pd.read_csv(data_dir / "raw" / "daily_observations.csv", parse_dates=["date"])
    events = pd.read_csv(
        data_dir / "scenarios" / "events.csv",
        parse_dates=["start_date", "end_date", "recovery_end_date"],
    )
    labels = pd.read_csv(data_dir / "processed" / "labels.csv", parse_dates=["as_of_date"])
    return {"merchants": merchants, "daily": daily, "events": events, "labels": labels}


def tag_active_event(daily: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `daily` with an `active_event_type` column: the
    event_type active on that merchant/day, or 'normal' if none. Relies on
    (and cross-checks) the no-self-overlap invariant — see
    check_structure()['self_overlapping_events'].
    """
    out = daily.copy()
    out["active_event_type"] = "normal"
    out["active_event_category"] = "normal"
    for _, ev in events.iterrows():
        mask = (
            (out["merchant_id"] == ev["merchant_id"])
            & (out["date"] >= ev["start_date"])
            & (out["date"] <= ev["recovery_end_date"])
        )
        out.loc[mask, "active_event_type"] = ev["event_type"]
        out.loc[mask, "active_event_category"] = ev["category"]
    return out


def add_rolling_chargeback_rate(daily: pd.DataFrame, window: int) -> pd.Series:
    """Causal (trailing-only) rolling chargeback rate, computed independently
    of labels.py, sorted/grouped by merchant then restored to original order.
    """
    d = daily.sort_values(["merchant_id", "day_index"])
    grp = d.groupby("merchant_id", sort=False)
    roll_cb = grp["chargeback_count"].transform(lambda s: s.rolling(window, min_periods=1).sum())
    roll_txn = grp["transaction_count"].transform(lambda s: s.rolling(window, min_periods=1).sum())
    rate = (roll_cb / roll_txn).reindex(daily.index)
    return rate


# ---------------------------------------------------------------------------
# 1. Dataset structure
# ---------------------------------------------------------------------------


def check_structure(tables: dict) -> dict:
    m, d, e, l = tables["merchants"], tables["daily"], tables["events"], tables["labels"]

    days_per_merchant = d.groupby("merchant_id").size()
    day_index_gaps = 0
    date_gaps = 0
    for _, g in d.groupby("merchant_id"):
        idx = g.sort_values("day_index")["day_index"].to_numpy()
        if not np.array_equal(idx, np.arange(len(idx))):
            day_index_gaps += 1
        dates = g.sort_values("date")["date"].to_numpy()
        expected = pd.date_range(dates.min(), dates.max(), freq="D").values
        if len(dates) != len(expected) or not np.array_equal(dates, expected):
            date_gaps += 1

    dup_merchants = int(m["merchant_id"].duplicated().sum())
    dup_daily = int(d.duplicated(subset=["merchant_id", "date"]).sum())
    dup_events = int(e["event_id"].duplicated().sum())
    dup_labels = int(l.duplicated(subset=["merchant_id", "as_of_date", "horizon_days"]).sum())

    null_counts = {
        "merchants": {c: int(n) for c, n in m.isna().sum().items() if n > 0},
        "daily": {c: int(n) for c, n in d.isna().sum().items() if n > 0},
        "events": {c: int(n) for c, n in e.isna().sum().items() if n > 0},
        "labels": {c: int(n) for c, n in l.isna().sum().items() if n > 0},
    }

    schema_mismatch = {
        "merchants": sorted(set(schema_columns("merchants")) ^ set(m.columns)),
        "daily": sorted(set(schema_columns("daily_observations")) ^ set(d.columns)),
        "events": sorted(set(schema_columns("events")) ^ set(e.columns)),
        "labels": sorted(set(schema_columns("labels")) ^ set(l.columns)),
    }

    dtypes = {
        "merchants": {c: str(t) for c, t in m.dtypes.items()},
        "daily": {c: str(t) for c, t in d.dtypes.items()},
        "events": {c: str(t) for c, t in e.dtypes.items()},
        "labels": {c: str(t) for c, t in l.dtypes.items()},
    }

    # Impossible / inconsistent value checks
    aov_consistency = np.isclose(d["aov"] * d["transaction_count"], d["gmv"], rtol=1e-6, atol=1e-3)
    payment_cols = [f"pct_pay_{m_}" for m_ in cfg.PAYMENT_METHODS]
    payment_mix_sum = d[payment_cols].sum(axis=1)

    self_overlaps = 0
    for _, g in e.sort_values("start_date").groupby("merchant_id"):
        prev_end = None
        for _, row in g.iterrows():
            if prev_end is not None and row["start_date"] <= prev_end:
                self_overlaps += 1
            prev_end = row["recovery_end_date"]

    impossible = {
        "negative_gmv": int((d["gmv"] < 0).sum()),
        "negative_transaction_count": int((d["transaction_count"] < 1).sum()),
        "negative_refund_amount": int((d["refund_amount"] < 0).sum()),
        "negative_chargeback_amount": int((d["chargeback_amount"] < 0).sum()),
        "negative_liquidity_balance": int((d["liquidity_balance"] < 0).sum()),
        "refund_amount_exceeds_gmv": int((d["refund_amount"] > d["gmv"] + 1e-6).sum()),
        "refund_count_exceeds_transactions": int((d["refund_count"] > d["transaction_count"]).sum()),
        "chargeback_count_exceeds_transactions": int((d["chargeback_count"] > d["transaction_count"]).sum()),
        "chargeback_amount_exceeds_gmv_same_day": int((d["chargeback_amount"] > d["gmv"]).sum()),
        "customer_split_inconsistent": int(
            (d["new_customers"] + d["returning_customers"] != d["customer_count"]).sum()
        ),
        "aov_times_txn_not_equal_gmv": int((~aov_consistency).sum()),
        "payment_mix_not_summing_to_one": int((~np.isclose(payment_mix_sum, 1.0, atol=1e-6)).sum()),
        "rates_out_of_unit_interval": {
            col: int((~d[col].between(0, 1)).sum())
            for col in ["refund_rate", "chargeback_rate", "fulfillment_on_time_rate", "new_customer_rate"]
        },
        "self_overlapping_events_per_merchant": self_overlaps,
    }

    return {
        "n_merchants": int(m["merchant_id"].nunique()),
        "n_daily_rows": int(len(d)),
        "days_per_merchant": {"min": int(days_per_merchant.min()), "max": int(days_per_merchant.max())},
        "date_range": {"min": str(d["date"].min().date()), "max": str(d["date"].max().date())},
        "merchants_with_day_index_gaps": int(day_index_gaps),
        "merchants_with_date_gaps": int(date_gaps),
        "duplicates": {
            "merchant_ids": dup_merchants,
            "daily_merchant_date_rows": dup_daily,
            "event_ids": dup_events,
            "label_merchant_asof_horizon_rows": dup_labels,
        },
        "null_counts": null_counts,
        "schema_column_mismatch": schema_mismatch,
        "dtypes": dtypes,
        "impossible_or_inconsistent_values": impossible,
    }


# ---------------------------------------------------------------------------
# 2. Merchant archetypes
# ---------------------------------------------------------------------------


def check_archetypes(tables: dict) -> dict:
    m, d = tables["merchants"], tables["daily"]
    counts = m["archetype"].value_counts().to_dict()
    mean_count = float(np.mean(list(counts.values())))
    underrepresented = {a: c for a, c in counts.items() if c < 0.7 * mean_count}

    merged = d.merge(m[["merchant_id", "archetype"]], on="merchant_id")
    behavior_cols = ["gmv", "aov", "refund_rate", "chargeback_rate", "fulfillment_on_time_rate", "new_customer_rate"]
    behavior_by_archetype = {
        col: merged.groupby("archetype")[col].median().round(6).to_dict() for col in behavior_cols
    }

    return {
        "merchant_counts_by_archetype": counts,
        "mean_merchants_per_archetype": mean_count,
        "archetypes_below_70pct_of_mean": underrepresented,
        "note": "50 merchants across 8 archetypes gives ~6-7 merchants/archetype by construction (even allocation, not random) — inherently small per-archetype N at this benchmark size, not a generator defect.",
        "median_behavior_by_archetype": behavior_by_archetype,
    }


# ---------------------------------------------------------------------------
# 3. Core distributions
# ---------------------------------------------------------------------------


def check_core_distributions(tables: dict) -> dict:
    d = tables["daily"]
    result = {
        "transaction_count": robust_summary(d["transaction_count"]),
        "gmv": robust_summary(d["gmv"]),
        "aov": robust_summary(d["aov"]),
        "refund_count": robust_summary(d["refund_count"]),
        "refund_rate": robust_summary(d["refund_rate"]),
        "chargeback_count": robust_summary(d["chargeback_count"]),
        "chargeback_rate": robust_summary(d["chargeback_rate"]),
        "fulfillment_on_time_rate": robust_summary(d["fulfillment_on_time_rate"]),
        "fulfillment_delay_avg_days": robust_summary(d["fulfillment_delay_avg_days"]),
        "new_customer_rate": robust_summary(d["new_customer_rate"]),
        "liquidity_balance": robust_summary(d["liquidity_balance"]),
        "pending_settlement_amount": robust_summary(d["pending_settlement_amount"]),
    }
    result["_gap_international_customer_share"] = (
        "NOT PRESENT in this benchmark. The generator models new_customers/returning_customers "
        "only; there is no domestic/international split anywhere in the schema. Reported here as "
        "a documented gap rather than fabricated or silently skipped."
    )
    return result


# ---------------------------------------------------------------------------
# 4. Scenario validation (+ shared risk-vs-benign pooled effect table used by
#    both section 4 and the hard-negative audit in section 7)
# ---------------------------------------------------------------------------


def pooled_effect_table(tagged_daily: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    merged = tagged_daily.merge(
        merchants[
            [
                "merchant_id",
                "baseline_daily_gmv",
                "baseline_daily_txn_count",
                "baseline_chargeback_rate",
                "baseline_refund_rate",
                "baseline_on_time_rate",
                "baseline_new_customer_rate",
            ]
        ],
        on="merchant_id",
    )
    rows = []
    for active_type, g in merged.groupby("active_event_type"):
        n_days = len(g)
        n_merchants = g["merchant_id"].nunique()
        gmv_ratio = g["gmv"].sum() / g["baseline_daily_gmv"].sum()
        txn_ratio = g["transaction_count"].sum() / g["baseline_daily_txn_count"].sum()
        cb_expected = (g["baseline_chargeback_rate"] * g["transaction_count"]).sum()
        cb_ratio = g["chargeback_count"].sum() / cb_expected if cb_expected > EPS else float("nan")
        refund_expected = (g["baseline_refund_rate"] * g["transaction_count"]).sum()
        refund_ratio = g["refund_count"].sum() / refund_expected if refund_expected > EPS else float("nan")
        on_time_delta = g["fulfillment_on_time_rate"].mean() - g["baseline_on_time_rate"].mean()
        new_cust_ratio = (
            g["new_customer_rate"].mean() / g["baseline_new_customer_rate"].mean()
            if g["baseline_new_customer_rate"].mean() > EPS
            else float("nan")
        )
        rows.append(
            {
                "active_event_type": active_type,
                "category": g["active_event_category"].iloc[0],
                "n_merchant_days": n_days,
                "n_distinct_merchants": n_merchants,
                "gmv_ratio_vs_baseline": gmv_ratio,
                "transaction_count_ratio_vs_baseline": txn_ratio,
                "new_customer_rate_ratio_vs_baseline": new_cust_ratio,
                "chargeback_rate_ratio_vs_baseline": cb_ratio,
                "refund_rate_ratio_vs_baseline": refund_ratio,
                "fulfillment_on_time_rate_delta_vs_baseline": on_time_delta,
            }
        )
    return pd.DataFrame(rows).sort_values("category").reset_index(drop=True)


def check_scenarios(tables: dict, tagged_daily: pd.DataFrame) -> dict:
    e, m = tables["events"], tables["merchants"]

    counts = e["event_type"].value_counts().to_dict()
    duration_by_type = {t: robust_summary(g["duration_days"]) for t, g in e.groupby("event_type")}
    severity_by_type = {t: robust_summary(g["severity_score"]) for t, g in e.groupby("event_type")}

    merged = e.merge(m[["merchant_id", "archetype"]], on="merchant_id")
    crosstab = pd.crosstab(merged["archetype"], merged["event_type"]).to_dict()
    crosstab = {et: {a: int(v) for a, v in per_archetype.items()} for et, per_archetype in crosstab.items()}

    concentration = {}
    for et, g in e.groupby("event_type"):
        n_events = len(g)
        n_merchants = g["merchant_id"].nunique()
        concentration[et] = {
            "n_events": int(n_events),
            "n_distinct_merchants": int(n_merchants),
            "events_per_merchant_that_has_it": round(n_events / n_merchants, 2),
        }

    pooled = pooled_effect_table(tagged_daily, m)

    # Does event-type assignment vary meaningfully by archetype, given it is
    # drawn from a single global weight distribution independent of
    # archetype? Chi-square-style dispersion check (no scipy dependency):
    # compare each archetype's share of each event_type against that
    # archetype's overall share of all events.
    archetype_share = merged["archetype"].value_counts(normalize=True).to_dict()
    expected_vs_observed = {}
    for et, g in merged.groupby("event_type"):
        observed_share = g["archetype"].value_counts(normalize=True).to_dict()
        expected_vs_observed[et] = {
            a: {
                "observed_share": round(observed_share.get(a, 0.0), 3),
                "expected_share_if_uniform": round(archetype_share.get(a, 0.0), 3),
            }
            for a in archetype_share
        }

    fulfillment_on_saas_digital = int(
        merged[
            (merged["event_type"] == "fulfillment_degradation")
            & (merged["archetype"].isin(["SaaS", "Digital Goods"]))
        ].shape[0]
    )

    return {
        "event_counts_by_type": counts,
        "duration_days_by_type": duration_by_type,
        "severity_score_by_type": severity_by_type,
        "archetype_x_event_type_crosstab": crosstab,
        "concentration_by_type": concentration,
        "archetype_share_of_events_by_type": expected_vs_observed,
        "fulfillment_degradation_events_on_saas_or_digital_goods": fulfillment_on_saas_digital,
        "note_event_assignment_is_archetype_agnostic": (
            "Event types are sampled from one global weight distribution (config.EVENT_TYPE_WEIGHTS) "
            "independent of archetype. This means, e.g., fulfillment_degradation can land on a SaaS or "
            "Digital Goods merchant whose baseline fulfillment delay is ~0 — mechanically harmless "
            "(values stay bounded) but semantically a weaker fit than for a physical-goods archetype. "
            "See fulfillment_degradation_events_on_saas_or_digital_goods above for how often this occurs."
        ),
        "pooled_effect_table": pooled.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# 5. Label analysis
# ---------------------------------------------------------------------------


def check_labels(tables: dict) -> dict:
    l, m = tables["labels"], tables["merchants"]
    merged = l.merge(m[["merchant_id", "archetype"]], on="merchant_id")

    by_horizon = {}
    for h, g in merged.groupby("horizon_days"):
        usable = len(g)
        positives = int(g["label_elevated_chargeback"].sum())
        negatives = usable - positives
        per_merchant_rate = g.groupby("merchant_id")["label_elevated_chargeback"].mean()
        per_archetype_rate = g.groupby("archetype")["label_elevated_chargeback"].mean()
        by_horizon[int(h)] = {
            "usable_rows": usable,
            "positives": positives,
            "negatives": negatives,
            "positive_rate": positives / usable if usable else float("nan"),
            "merchant_level_positive_rate": {
                "min": float(per_merchant_rate.min()),
                "median": float(per_merchant_rate.median()),
                "max": float(per_merchant_rate.max()),
                "n_merchants_with_zero_positives": int((per_merchant_rate == 0).sum()),
                "n_merchants_all_positive": int((per_merchant_rate == 1).sum()),
                "n_merchants_total": int(per_merchant_rate.shape[0]),
            },
            "archetype_level_positive_rate": per_archetype_rate.round(4).to_dict(),
        }

    rates = [v["positive_rate"] for v in by_horizon.values()]
    imbalance_assessment = (
        "manageable" if all(0.05 <= r <= 0.60 for r in rates) else "check manually — outside [5%, 60%] band"
    )

    return {"by_horizon": by_horizon, "imbalance_assessment": imbalance_assessment}


# ---------------------------------------------------------------------------
# 6. Horizon comparison
# ---------------------------------------------------------------------------


def check_horizon_comparison(tables: dict) -> dict:
    l = tables["labels"]
    wide = l.pivot_table(
        index=["merchant_id", "as_of_date"], columns="horizon_days", values="label_elevated_chargeback"
    )
    wide.columns = [f"h{int(c)}" for c in wide.columns]
    common = wide.dropna()  # rows where all three horizons are defined for the same as_of_date

    prevalence_common_subset = {c: float(common[c].mean()) for c in common.columns}

    def conditional(a, b):
        sub = common[common[a] == 1]
        return float(sub[b].mean()) if len(sub) else float("nan")

    conditionals = {}
    for a in ["h7", "h14", "h30"]:
        for b in ["h7", "h14", "h30"]:
            if a != b:
                conditionals[f"P({b}=1|{a}=1)"] = conditional(a, b)

    def jaccard(a, b):
        A = set(common.index[common[a] == 1])
        B = set(common.index[common[b] == 1])
        union = A | B
        return len(A & B) / len(union) if union else float("nan")

    jaccards = {
        "h7_vs_h14": jaccard("h7", "h14"),
        "h7_vs_h30": jaccard("h7", "h30"),
        "h14_vs_h30": jaccard("h14", "h30"),
    }

    all_agree = ((common["h7"] == common["h14"]) & (common["h14"] == common["h30"])).mean()

    return {
        "n_rows_with_all_three_horizons_defined": int(len(common)),
        "prevalence_on_common_subset": prevalence_common_subset,
        "conditional_probabilities": conditionals,
        "jaccard_overlap_of_positive_sets": jaccards,
        "fraction_all_three_horizons_agree": float(all_agree),
    }


# ---------------------------------------------------------------------------
# 7. Hard-negative audit (reuses the pooled effect table from section 4)
# ---------------------------------------------------------------------------


def check_hard_negative_audit(pooled: pd.DataFrame) -> dict:
    benign = pooled[pooled["category"] == cfg.EVENT_CATEGORY_BENIGN_GROWTH]
    risk = pooled[pooled["category"] == cfg.EVENT_CATEGORY_RISK]
    normal = pooled[pooled["active_event_type"] == "normal"]

    def agg(df, cols):
        weights = df["n_merchant_days"]
        return {c: float(np.average(df[c], weights=weights)) for c in cols}

    cols = [
        "gmv_ratio_vs_baseline",
        "transaction_count_ratio_vs_baseline",
        "chargeback_rate_ratio_vs_baseline",
        "refund_rate_ratio_vs_baseline",
        "fulfillment_on_time_rate_delta_vs_baseline",
    ]

    benign_summary = agg(benign, cols) if len(benign) else {}
    risk_summary = agg(risk, cols) if len(risk) else {}
    normal_summary = agg(normal, cols) if len(normal) else {}

    verdict_growth_not_risk = bool(
        benign_summary.get("gmv_ratio_vs_baseline", 0) > 1.3
        and benign_summary.get("chargeback_rate_ratio_vs_baseline", 99) < 1.5
        and benign_summary.get("refund_rate_ratio_vs_baseline", 99) < 1.5
        and risk_summary.get("chargeback_rate_ratio_vs_baseline", 0) > benign_summary.get("chargeback_rate_ratio_vs_baseline", 0)
    )

    return {
        "per_event_type": pooled.set_index("active_event_type")[cols].round(4).to_dict(orient="index"),
        "benign_growth_volume_weighted_average": benign_summary,
        "risk_volume_weighted_average": risk_summary,
        "normal_periods_volume_weighted_average": normal_summary,
        "growth_ne_risk_verdict": verdict_growth_not_risk,
    }


# ---------------------------------------------------------------------------
# 8. Temporal / warning structure
# ---------------------------------------------------------------------------


def check_temporal_warning_structure(tables: dict) -> dict:
    d, e = tables["daily"], tables["events"]
    d = d.copy()
    d["roll_cb_rate_7d"] = add_rolling_chargeback_rate(d, window=7)
    # Per-merchant array indexed by day_index, for fast offset lookups below.
    per_merchant_series = {
        mid: g.sort_values("day_index").set_index("day_index")["roll_cb_rate_7d"]
        for mid, g in d.groupby("merchant_id")
    }
    max_day_index = int(d["day_index"].max())

    risk_types = ["chargeback_deterioration", "refund_shock", "fulfillment_degradation", "customer_mix_shift", "compound_risk"]
    result = {}
    for et in risk_types:
        instances = e[e["event_type"] == et]
        offsets = range(-20, 61)
        offset_values: dict[int, list[float]] = {o: [] for o in offsets}
        detection_offsets = []
        for _, ev in instances.iterrows():
            series = per_merchant_series[ev["merchant_id"]]
            start_day = (ev["start_date"] - d["date"].min()).days
            pre = [
                series.get(start_day + o)
                for o in range(-20, 0)
                if 0 <= start_day + o <= max_day_index
            ]
            pre = [v for v in pre if v is not None and not np.isnan(v)]
            baseline = float(np.mean(pre)) if len(pre) >= 5 else None

            for o in offsets:
                day_idx = start_day + o
                if 0 <= day_idx <= max_day_index:
                    v = series.get(day_idx)
                    if v is not None and not np.isnan(v):
                        offset_values[o].append(float(v))

            if baseline is not None:
                threshold = max(baseline * 1.3, baseline + 0.003, 0.004)
                detected = None
                for o in range(3, 71):
                    day_idx = start_day + o
                    window_vals = [
                        series.get(day_idx + k) for k in range(0, 3) if 0 <= day_idx + k <= max_day_index
                    ]
                    window_vals = [v for v in window_vals if v is not None and not np.isnan(v)]
                    if len(window_vals) == 3 and np.mean(window_vals) >= threshold:
                        detected = o
                        break
                detection_offsets.append(detected)

        n_detected = sum(1 for x in detection_offsets if x is not None)
        detected_vals = [x for x in detection_offsets if x is not None]
        result[et] = {
            "n_instances": int(len(instances)),
            "n_instances_with_valid_pre_window": len(detection_offsets),
            "n_instances_with_detectable_uplift": n_detected,
            "fraction_detectable": n_detected / len(detection_offsets) if detection_offsets else float("nan"),
            "median_detection_offset_days": float(np.median(detected_vals)) if detected_vals else None,
            "p25_detection_offset_days": float(np.percentile(detected_vals, 25)) if detected_vals else None,
            "p75_detection_offset_days": float(np.percentile(detected_vals, 75)) if detected_vals else None,
            "mean_rolling_chargeback_rate_by_offset": {
                str(o): (float(np.mean(v)) if v else None) for o, v in offset_values.items()
            },
        }

    return result


# ---------------------------------------------------------------------------
# 9. Leakage audit
# ---------------------------------------------------------------------------


def check_leakage_audit(tables: dict) -> dict:
    m, d, e, l = tables["merchants"], tables["daily"], tables["events"], tables["labels"]

    label_derived_terms = ["future_", "elevation_ratio", "label_elevated"]
    daily_columns_matching = [c for c in d.columns if any(t in c for t in label_derived_terms)]

    forbidden_merchant_columns = [
        "baseline_daily_gmv",
        "baseline_daily_txn_count",
        "baseline_aov",
        "baseline_refund_rate",
        "baseline_chargeback_rate",
        "baseline_fulfillment_delay_days",
        "baseline_on_time_rate",
        "baseline_new_customer_rate",
        "baseline_pct_pay_card",
        "baseline_pct_pay_upi",
        "baseline_pct_pay_netbanking",
        "baseline_pct_pay_wallet",
        "baseline_pct_pay_bnpl",
        "annual_growth_rate",
        "volatility_factor",
    ]

    # Quantify how much "cheating" the generator's ground-truth baseline
    # would buy if misused directly as a feature (it must not be).
    l_merged = l.merge(m[["merchant_id", "baseline_chargeback_rate"]], on="merchant_id")
    ground_truth_baseline_auc = {
        int(h): auc_from_scores(g["baseline_chargeback_rate"].to_numpy(), g["label_elevated_chargeback"].to_numpy())
        for h, g in l_merged.groupby("horizon_days")
    }

    # Quantify how much "cheating" using the raw ground-truth event
    # category (risk vs not) as a feature would buy — this is the clearest
    # possible illustration of why events.csv must never be joined into a
    # feature matrix.
    tagged = tag_active_event(d, e)
    tagged["is_risk_day"] = (tagged["active_event_category"] == cfg.EVENT_CATEGORY_RISK).astype(int)
    l_tagged = l.merge(tagged[["merchant_id", "day_index", "is_risk_day"]], on=["merchant_id", "day_index"])
    ground_truth_event_flag_auc = {
        int(h): auc_from_scores(g["is_risk_day"].to_numpy(), g["label_elevated_chargeback"].to_numpy())
        for h, g in l_tagged.groupby("horizon_days")
    }

    return {
        "daily_observations_columns_matching_label_terms": daily_columns_matching,
        "forbidden_feature_sources": {
            "merchants.csv": {
                "columns": forbidden_merchant_columns,
                "reason": "Generator ground-truth parameters, not observable to a real merchant-risk system. Strongly correlated with the label by construction (they parametrize its generation).",
            },
            "events.csv": {
                "columns": list(e.columns),
                "reason": "Ground-truth scenario identity/timing/severity. Joining ANY column from this table onto a feature matrix is direct label leakage — it tells the model exactly when a risk episode is happening.",
            },
            "labels.csv (columns beyond the join keys and the target itself)": {
                "columns": [
                    "future_chargeback_amount",
                    "future_chargeback_rate",
                    "future_transaction_count",
                    "elevation_ratio_amount",
                    "elevation_ratio_rate",
                    "baseline_daily_gmv_trailing",
                    "baseline_daily_chargeback_amount_trailing",
                    "baseline_chargeback_rate_trailing",
                ],
                "reason": "future_* and elevation_ratio_* are target-adjacent by construction. The baseline_*_trailing columns are individually leakage-free (past-only) but sit in the same table as the target — feature engineering should recompute trailing baselines directly from daily_observations, not import them from here.",
            },
        },
        "diagnostic_auc_if_ground_truth_baseline_chargeback_rate_used_as_a_feature": ground_truth_baseline_auc,
        "diagnostic_auc_if_ground_truth_risk_event_flag_used_as_a_feature": ground_truth_event_flag_auc,
        "interpretation": (
            "Both diagnostic AUCs above are expected to be well above what any legitimate feature "
            "achieves (see check_difficulty_audit). That gap is the point: it demonstrates concretely "
            "what leakage would buy, as a warning for the feature-engineering stage, not a proposal to "
            "use these columns."
        ),
    }


# ---------------------------------------------------------------------------
# 10. Prediction-difficulty audit
# ---------------------------------------------------------------------------


def check_difficulty_audit(tables: dict) -> dict:
    d, l = tables["daily"], tables["labels"]
    d = d.copy()
    d["trailing_chargeback_rate_28d"] = add_rolling_chargeback_rate(d, window=28)
    d["trailing_gmv_28d_mean"] = (
        d.sort_values(["merchant_id", "day_index"])
        .groupby("merchant_id")["gmv"]
        .transform(lambda s: s.rolling(28, min_periods=1).mean())
        .reindex(d.index)
    )

    merged = l.merge(
        d[["merchant_id", "day_index", "chargeback_rate", "gmv", "trailing_chargeback_rate_28d", "trailing_gmv_28d_mean"]],
        on=["merchant_id", "day_index"],
        how="left",
    )

    candidate_features = {
        "same_day_raw_chargeback_rate": "chargeback_rate",
        "same_day_raw_gmv": "gmv",
        "trailing_28d_chargeback_rate (legitimate, causal)": "trailing_chargeback_rate_28d",
        "trailing_28d_mean_gmv (legitimate, causal)": "trailing_gmv_28d_mean",
    }

    auc_by_horizon = {}
    for h, g in merged.groupby("horizon_days"):
        auc_by_horizon[int(h)] = {
            name: auc_from_scores(g[col].to_numpy(), g["label_elevated_chargeback"].to_numpy())
            for name, col in candidate_features.items()
        }

    # Threshold-boundary sensitivity: how many rows sit close to the
    # elevation-ratio decision boundary (1.75x)?
    threshold = cfg.LABEL_ELEVATION_RATIO_THRESHOLD
    near_boundary_frac = float(
        (l["elevation_ratio_amount"].sub(threshold).abs() < 0.1 * threshold).mean()
    )

    max_legit_auc = max(
        max(v for k, v in row.items() if "legitimate" in k) for row in auc_by_horizon.values()
    )
    min_legit_auc = min(
        min(v for k, v in row.items() if "legitimate" in k) for row in auc_by_horizon.values()
    )

    assessment = []
    if max_legit_auc > 0.97:
        assessment.append("a legitimate single feature is suspiciously close to perfect — investigate for leakage")
    if min_legit_auc < 0.55:
        assessment.append("legitimate features show weak signal on at least one horizon — label may be hard to learn at that horizon")
    if not assessment:
        assessment.append("legitimate single-feature AUCs sit in a plausible 'some signal, not trivial' band")

    return {
        "single_feature_auc_by_horizon": auc_by_horizon,
        "fraction_labels_within_10pct_of_elevation_ratio_threshold": near_boundary_frac,
        "assessment": assessment,
    }


# ---------------------------------------------------------------------------
# 11. Archetype bias audit
# ---------------------------------------------------------------------------


def check_archetype_bias(tables: dict) -> dict:
    l, m = tables["labels"], tables["merchants"]
    merged = l.merge(m[["merchant_id", "archetype"]], on="merchant_id")

    result = {}
    for h, g in merged.groupby("horizon_days"):
        rate_by_archetype = g.groupby("archetype")["label_elevated_chargeback"].mean()
        mean_encoded_score = g["archetype"].map(rate_by_archetype)
        auc = auc_from_scores(mean_encoded_score.to_numpy(), g["label_elevated_chargeback"].to_numpy())
        result[int(h)] = {
            "positive_rate_by_archetype": rate_by_archetype.round(4).to_dict(),
            "max_over_min_ratio": float(rate_by_archetype.max() / max(rate_by_archetype.min(), EPS)),
            "archetype_mean_encoded_auc": auc,
        }

    max_auc = max(v["archetype_mean_encoded_auc"] for v in result.values())
    flag = max_auc > 0.65
    return {"by_horizon": result, "archetype_alone_is_a_meaningful_shortcut": bool(flag), "max_auc_across_horizons": max_auc}


# ---------------------------------------------------------------------------
# 12. Financial consistency
# ---------------------------------------------------------------------------


def check_financial_consistency(tables: dict, tagged_daily: pd.DataFrame) -> dict:
    d, m = tables["daily"], tables["merchants"]

    cb_to_gmv_ratio = (d["chargeback_amount"] / d["gmv"]).replace([np.inf, -np.inf], np.nan)
    refund_to_gmv_ratio = (d["refund_amount"] / d["gmv"]).replace([np.inf, -np.inf], np.nan)

    merged = d.merge(m[["merchant_id", "settlement_cycle_days"]], on="merchant_id")
    pending_ratio = merged["pending_settlement_amount"] / (merged["settlement_cycle_days"] * merged["gmv"].clip(lower=1))

    # Liquidity trajectory by active event category: mean per-day change in
    # liquidity_balance relative to the merchant's target buffer scale.
    td = tagged_daily.merge(m[["merchant_id", "baseline_daily_gmv", "liquidity_buffer_days"]], on="merchant_id")
    td["liquidity_delta"] = td.sort_values(["merchant_id", "day_index"]).groupby("merchant_id")["liquidity_balance"].diff()
    td["liquidity_scale"] = td["baseline_daily_gmv"] * td["liquidity_buffer_days"]
    td["normalized_liquidity_delta"] = td["liquidity_delta"] / td["liquidity_scale"]
    liquidity_trend_by_category = (
        td.groupby("active_event_category")["normalized_liquidity_delta"].mean().round(6).to_dict()
    )

    return {
        "chargeback_amount_to_gmv_ratio": robust_summary(cb_to_gmv_ratio),
        "refund_amount_to_gmv_ratio": robust_summary(refund_to_gmv_ratio),
        "days_chargeback_amount_exceeds_same_day_gmv": int((d["chargeback_amount"] > d["gmv"]).sum()),
        "pending_settlement_to_expected_scale_ratio": robust_summary(pending_ratio),
        "mean_normalized_daily_liquidity_change_by_active_event_category": liquidity_trend_by_category,
        "note_chargeback_same_day_gmv_comparison": (
            "chargeback_amount(t) is modeled against transactions dated t in this simplified generator; "
            "in reality chargebacks reference historical orders, so exceeding same-day GMV is not "
            "'impossible' in the real world, only a simplification here. Frequency above should still be low."
        ),
    }
