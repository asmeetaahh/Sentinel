"""
SENTINEL SYNTHETIC PROTOTYPE REASON-CODE TAXONOMY.

This is NOT Razorpay's, Visa's, Mastercard's, or any card network's
proprietary dispute reason-code taxonomy. It is a small, fixed,
deterministic mapping this prototype invented to give each incident a
controlled category (rather than free text), so evidence requirements can
be attached predictably. See docs/architecture/incident_response.md.

Mapping rationale (one reason code per synthetic risk event_type — see
ml/data_generation/config.py:EVENT_TYPES and docs/architecture/data_generation.md):

- fulfillment_degradation -> GOODS_OR_SERVICE_NOT_RECEIVED
    The event's own `affects` columns are fulfillment_on_time_rate,
    fulfillment_delay_avg_days, and a linked chargeback_rate increase —
    late/failed delivery driving disputes is the direct real-world analog.
- refund_shock -> CREDIT_NOT_PROCESSED
    A spike in refund_rate mapped to "customer disputes an expected but
    unresolved credit."
- chargeback_deterioration -> SUSPECTED_FRAUD_OR_UNAUTHORIZED
    This event type touches ONLY chargeback_rate (no refund/fulfillment/
    customer-mix signal) — the natural catch-all category for a chargeback
    increase with no other observable operational cause.
- customer_mix_shift -> UNRECOGNIZED_TRANSACTION
    A rising new-customer share followed by a lagged chargeback increase —
    unfamiliar first-time purchasers are the plausible synthetic analog for
    "cardholder doesn't recognize this charge."
- compound_risk -> MULTIPLE_FACTORS
    Bundles refund, chargeback, and fulfillment effects in one event —
    genuinely multi-causal, so it gets its own code rather than being
    forced into one of the above.

Every one of these is a PROTOTYPE mapping choice, not a verified real-world
correspondence. It exists so the evidence-readiness engine has a controlled
input, not to claim clinical accuracy about why a given chargeback occurred.
"""

from __future__ import annotations

from dataclasses import dataclass

GOODS_OR_SERVICE_NOT_RECEIVED = "GOODS_OR_SERVICE_NOT_RECEIVED"
CREDIT_NOT_PROCESSED = "CREDIT_NOT_PROCESSED"
SUSPECTED_FRAUD_OR_UNAUTHORIZED = "SUSPECTED_FRAUD_OR_UNAUTHORIZED"
UNRECOGNIZED_TRANSACTION = "UNRECOGNIZED_TRANSACTION"
MULTIPLE_FACTORS = "MULTIPLE_FACTORS"

EVENT_TYPE_TO_REASON_CODE: dict[str, str] = {
    "fulfillment_degradation": GOODS_OR_SERVICE_NOT_RECEIVED,
    "refund_shock": CREDIT_NOT_PROCESSED,
    "chargeback_deterioration": SUSPECTED_FRAUD_OR_UNAUTHORIZED,
    "customer_mix_shift": UNRECOGNIZED_TRANSACTION,
    "compound_risk": MULTIPLE_FACTORS,
}

REASON_CODE_LABELS: dict[str, str] = {
    GOODS_OR_SERVICE_NOT_RECEIVED: "Goods or service not received",
    CREDIT_NOT_PROCESSED: "Credit not processed",
    SUSPECTED_FRAUD_OR_UNAUTHORIZED: "Suspected fraud or unauthorized transaction",
    UNRECOGNIZED_TRANSACTION: "Unrecognized transaction",
    MULTIPLE_FACTORS: "Multiple contributing factors",
}

REASON_CODE_DESCRIPTIONS: dict[str, str] = {
    GOODS_OR_SERVICE_NOT_RECEIVED: (
        "Associated with a synthetic fulfillment-degradation episode: declining on-time delivery "
        "and rising delay, with a linked chargeback increase."
    ),
    CREDIT_NOT_PROCESSED: "Associated with a synthetic refund-shock episode: a spike in the merchant's refund rate.",
    SUSPECTED_FRAUD_OR_UNAUTHORIZED: (
        "Associated with a synthetic chargeback-deterioration episode: a chargeback-rate increase "
        "with no accompanying refund, fulfillment, or customer-mix signal."
    ),
    UNRECOGNIZED_TRANSACTION: (
        "Associated with a synthetic customer-mix-shift episode: a rising new-customer share followed "
        "by a lagged chargeback increase."
    ),
    MULTIPLE_FACTORS: (
        "Associated with a synthetic compound-risk episode bundling refund, chargeback, and "
        "fulfillment effects together."
    ),
}

# ---------------------------------------------------------------------------
# Evidence categories — a controlled taxonomy, matching PROJECT_CONTEXT.md's
# "possible evidence" list exactly.
# ---------------------------------------------------------------------------

INVOICE = "invoice"
PAYMENT_CONFIRMATION = "payment_confirmation"
DELIVERY_PROOF = "delivery_proof"
TRACKING_INFORMATION = "tracking_information"
REFUND_CONFIRMATION = "refund_confirmation"
CUSTOMER_COMMUNICATION = "customer_communication"
SERVICE_ACCESS_RECORDS = "service_access_records"

EVIDENCE_LABELS: dict[str, str] = {
    INVOICE: "Invoice",
    PAYMENT_CONFIRMATION: "Payment confirmation",
    DELIVERY_PROOF: "Delivery proof",
    TRACKING_INFORMATION: "Tracking information",
    REFUND_CONFIRMATION: "Refund confirmation",
    CUSTOMER_COMMUNICATION: "Customer communication",
    SERVICE_ACCESS_RECORDS: "Service / access records",
}

# Fixed, disclosed importance ordering used only to sort a MISSING-evidence
# list for display (most commonly dispute-critical first) — not a model,
# not tuned, the same order regardless of incident.
EVIDENCE_PRIORITY_ORDER: list[str] = [
    PAYMENT_CONFIRMATION,
    INVOICE,
    DELIVERY_PROOF,
    TRACKING_INFORMATION,
    REFUND_CONFIRMATION,
    CUSTOMER_COMMUNICATION,
    SERVICE_ACCESS_RECORDS,
]

# Required evidence per reason code — deterministic, fixed, documented.
REASON_CODE_REQUIRED_EVIDENCE: dict[str, list[str]] = {
    GOODS_OR_SERVICE_NOT_RECEIVED: [INVOICE, PAYMENT_CONFIRMATION, DELIVERY_PROOF, TRACKING_INFORMATION],
    CREDIT_NOT_PROCESSED: [INVOICE, PAYMENT_CONFIRMATION, REFUND_CONFIRMATION, CUSTOMER_COMMUNICATION],
    SUSPECTED_FRAUD_OR_UNAUTHORIZED: [INVOICE, PAYMENT_CONFIRMATION, CUSTOMER_COMMUNICATION, SERVICE_ACCESS_RECORDS],
    UNRECOGNIZED_TRANSACTION: [INVOICE, PAYMENT_CONFIRMATION, CUSTOMER_COMMUNICATION, SERVICE_ACCESS_RECORDS],
    MULTIPLE_FACTORS: [
        INVOICE,
        PAYMENT_CONFIRMATION,
        DELIVERY_PROOF,
        TRACKING_INFORMATION,
        REFUND_CONFIRMATION,
        CUSTOMER_COMMUNICATION,
    ],
}


@dataclass(frozen=True)
class ReasonCode:
    code: str
    label: str
    description: str
    required_evidence: list[str]


def reason_code_for_event_type(event_type: str) -> ReasonCode:
    code = EVENT_TYPE_TO_REASON_CODE.get(event_type)
    if code is None:
        raise ValueError(f"No reason-code mapping for event_type={event_type!r} (expected a risk-category event type).")
    return ReasonCode(
        code=code,
        label=REASON_CODE_LABELS[code],
        description=REASON_CODE_DESCRIPTIONS[code],
        required_evidence=list(REASON_CODE_REQUIRED_EVIDENCE[code]),
    )
