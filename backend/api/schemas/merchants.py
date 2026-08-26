from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .common import Provenance


class MerchantListItem(BaseModel):
    merchant_id: str
    archetype: str
    business_tier: str
    signup_date: date


class MerchantListResponse(BaseModel):
    count: int
    merchants: list[MerchantListItem]


class BenchmarkHistory(BaseModel):
    first_date: date
    last_date: date
    n_days: int


class LatestObservedSnapshot(BaseModel):
    as_of_date: date
    day_index: int
    gmv: float
    transaction_count: int
    chargeback_rate: float
    refund_rate: float
    fulfillment_on_time_rate: float
    liquidity_balance: float
    provenance: Provenance


class MerchantProfileResponse(BaseModel):
    merchant_id: str
    archetype: str
    business_tier: str
    signup_date: date
    weekly_seasonality_profile: str
    benchmark_history: BenchmarkHistory
    latest_observed_snapshot: LatestObservedSnapshot


class ObservationRecord(BaseModel):
    date: date
    day_index: int
    gmv: float
    transaction_count: int
    aov: float
    refund_count: int
    refund_amount: float
    refund_rate: float
    chargeback_count: int
    chargeback_amount: float
    chargeback_rate: float
    fulfillment_delay_avg_days: float
    fulfillment_on_time_rate: float
    customer_count: int
    new_customers: int
    returning_customers: int
    new_customer_rate: float
    pct_pay_card: float
    pct_pay_upi: float
    pct_pay_netbanking: float
    pct_pay_wallet: float
    pct_pay_bnpl: float
    liquidity_balance: float
    pending_settlement_amount: float


class ObservationsResponse(BaseModel):
    merchant_id: str
    count: int
    observations: list[ObservationRecord]


class FeatureEntry(BaseModel):
    feature: str
    value: float
    group: str
    definition: str
    window: str | None
    kind: str


class FeatureVectorResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    day_index: int
    n_features: int
    features: list[FeatureEntry]
