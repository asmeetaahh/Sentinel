"""
Deterministic evidence-readiness engine.

This NEVER fabricates an actual document, tracking number, invoice, or
message. It only ever answers a yes/no "is this evidence category
plausibly available" question, using one of two kinds of input:

  1. An OBSERVED benchmark signal for this merchant's incident window
     (e.g. the window's mean fulfillment_on_time_rate), when one exists.
  2. An explicitly documented SYNTHETIC/PROTOTYPE business assumption
     (e.g. "larger merchants are assumed to already log customer support
     communication"), when no benchmark signal exists for that evidence
     category at all.

Every rule below is fixed and disclosed here — see
docs/architecture/incident_response.md for the full rationale. None of
these thresholds were tuned to make any particular incident "look" more or
less ready; they were chosen once, before looking at incident-level results.
"""

from __future__ import annotations

import pandas as pd

from backend.evidence.reason_codes import (
    CUSTOMER_COMMUNICATION,
    DELIVERY_PROOF,
    EVIDENCE_LABELS,
    EVIDENCE_PRIORITY_ORDER,
    INVOICE,
    PAYMENT_CONFIRMATION,
    REFUND_CONFIRMATION,
    SERVICE_ACCESS_RECORDS,
    TRACKING_INFORMATION,
    ReasonCode,
)

# Prototype assumption: below this window-mean on-time fulfillment rate,
# delivery proof / tracking are assumed incomplete or unavailable — the same
# operational breakdown that plausibly caused the fulfillment-related
# dispute in the first place plausibly also left its own paper trail
# incomplete. Fixed at 0.70, not tuned per-incident.
FULFILLMENT_EVIDENCE_COMPLETENESS_THRESHOLD = 0.70

# Archetypes for which a digital service/access log is a natural part of
# the business (prototype assumption — see docs/architecture/incident_response.md).
SERVICE_ACCESS_LOG_ARCHETYPES = {"SaaS", "Digital Goods"}

# Business tiers assumed, as a prototype heuristic, to already have a basic
# support-communication logging process in place.
COMMUNICATION_LOG_TIERS = {"mid", "large"}


def _window_slice(daily_observations: pd.DataFrame, merchant_id: str, start_day: int, end_day: int) -> pd.DataFrame:
    merchant_daily = daily_observations[daily_observations["merchant_id"] == merchant_id]
    return merchant_daily[(merchant_daily["day_index"] >= start_day) & (merchant_daily["day_index"] <= end_day)]


def _window_mean_fulfillment_rate(daily_observations: pd.DataFrame, merchant_id: str, start_day: int, end_day: int) -> float:
    window = _window_slice(daily_observations, merchant_id, start_day, end_day)
    weighted = (window["fulfillment_on_time_rate"] * window["transaction_count"]).sum()
    total_txns = window["transaction_count"].sum()
    return float(weighted / total_txns) if total_txns > 0 else 1.0


def _window_sum_refund_count(daily_observations: pd.DataFrame, merchant_id: str, start_day: int, end_day: int) -> int:
    window = _window_slice(daily_observations, merchant_id, start_day, end_day)
    return int(window["refund_count"].sum())


def readiness_status_from_counts(available_count: int, required_count: int) -> str:
    """Pure classification, isolated from the counting logic so it can be
    tested exhaustively on its own. `required_count` is always >= 1 for a
    real reason code (every entry in REASON_CODE_REQUIRED_EVIDENCE is
    non-empty); guarded here anyway rather than assumed.
    """
    if required_count <= 0:
        return "ready"
    if available_count >= required_count:
        return "ready"
    if available_count <= 0:
        return "insufficient"
    return "partial"


def _evidence_item(category: str, required: bool, available: bool, rationale: str, provenance: str) -> dict:
    return {
        "category": category,
        "label": EVIDENCE_LABELS[category],
        "required": required,
        "available": available,
        "rationale": rationale,
        "provenance": provenance,
    }


def compute_evidence_readiness(
    daily_observations: pd.DataFrame,
    merchant_row: pd.Series,
    reason_code: ReasonCode,
    start_day: int,
    end_day: int,
) -> dict:
    merchant_id = merchant_row["merchant_id"]
    required_set = set(reason_code.required_evidence)

    fulfillment_rate = _window_mean_fulfillment_rate(daily_observations, merchant_id, start_day, end_day)
    refund_count = _window_sum_refund_count(daily_observations, merchant_id, start_day, end_day)
    archetype = merchant_row["archetype"]
    business_tier = merchant_row["business_tier"]

    items: list[dict] = []

    items.append(
        _evidence_item(
            INVOICE,
            INVOICE in required_set,
            True,
            "Prototype assumption: an invoice/receipt is treated as always available for a processed transaction "
            "in this benchmark — not verified per transaction.",
            "synthetic_prototype",
        )
    )
    items.append(
        _evidence_item(
            PAYMENT_CONFIRMATION,
            PAYMENT_CONFIRMATION in required_set,
            True,
            "Prototype assumption: a payment confirmation is treated as always available for any transaction "
            "processed through the platform.",
            "synthetic_prototype",
        )
    )

    fulfillment_ok = fulfillment_rate >= FULFILLMENT_EVIDENCE_COMPLETENESS_THRESHOLD
    fulfillment_rationale = (
        f"Derived from this merchant's OBSERVED on-time fulfillment rate during the incident window "
        f"({fulfillment_rate:.0%}), {'at or above' if fulfillment_ok else 'below'} the "
        f"{FULFILLMENT_EVIDENCE_COMPLETENESS_THRESHOLD:.0%} completeness assumption used by this prototype."
    )
    items.append(_evidence_item(DELIVERY_PROOF, DELIVERY_PROOF in required_set, fulfillment_ok, fulfillment_rationale, "derived"))
    items.append(
        _evidence_item(TRACKING_INFORMATION, TRACKING_INFORMATION in required_set, fulfillment_ok, fulfillment_rationale, "derived")
    )

    refund_available = refund_count > 0
    items.append(
        _evidence_item(
            REFUND_CONFIRMATION,
            REFUND_CONFIRMATION in required_set,
            refund_available,
            f"Derived from this merchant's OBSERVED refund_count during the incident window (sum={refund_count}); "
            + ("a refund was recorded, so a confirmation exists." if refund_available else "no refund was recorded in this window, so no confirmation exists."),
            "derived",
        )
    )

    communication_available = business_tier in COMMUNICATION_LOG_TIERS
    items.append(
        _evidence_item(
            CUSTOMER_COMMUNICATION,
            CUSTOMER_COMMUNICATION in required_set,
            communication_available,
            f"Prototype assumption: business_tier={business_tier!r} is "
            + ("assumed to already have a support-communication log in place." if communication_available else "assumed not to have a systematic support-communication log in place.")
            + " Not derived from any real communication data — this benchmark contains none.",
            "synthetic_prototype",
        )
    )

    access_available = archetype in SERVICE_ACCESS_LOG_ARCHETYPES
    items.append(
        _evidence_item(
            SERVICE_ACCESS_RECORDS,
            SERVICE_ACCESS_RECORDS in required_set,
            access_available,
            f"Prototype assumption: archetype={archetype!r} is "
            + ("assumed to naturally produce digital service/access logs." if access_available else "assumed not to naturally produce digital service/access logs (a physical-goods or offline-service business).")
            + " Not derived from any real access-log data — this benchmark contains none.",
            "synthetic_prototype",
        )
    )

    required_items = [item for item in items if item["required"]]
    available_required = [item for item in required_items if item["available"]]
    missing_required = [item for item in required_items if not item["available"]]
    missing_sorted = sorted(missing_required, key=lambda item: EVIDENCE_PRIORITY_ORDER.index(item["category"]))

    required_count = len(required_items)
    available_count = len(available_required)
    readiness_status = readiness_status_from_counts(available_count, required_count)

    return {
        "reason_code": reason_code.code,
        "required_evidence": reason_code.required_evidence,
        "items": items,
        "required_count": required_count,
        "available_count": available_count,
        "missing_evidence": [item["category"] for item in missing_sorted],
        "readiness_status": readiness_status,
        "disclaimer": (
            "Evidence availability shown here is derived from observed benchmark signals or explicitly documented "
            "prototype assumptions — never a real document, tracking number, invoice, or message. No evidence "
            "artifact is fabricated. See docs/architecture/incident_response.md."
        ),
    }
