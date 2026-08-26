/**
 * TypeScript types mirroring the backend's Pydantic response schemas
 * exactly (see backend/api/schemas/*.py). Keep in sync with the backend —
 * these are not independently invented shapes.
 */

export type Provenance = 'observed' | 'modeled' | 'derived'

// ---------------------------------------------------------------------------
// Health / metadata
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string
}

export interface ModelMetadataResponse {
  artifact_id: string
  horizon_days: number
  decision_threshold: number
  calibration_method: string
  n_features: number
  seed: number
  dataset_fingerprint_sha256_16: Record<string, string>
  disclaimer: string
}

// ---------------------------------------------------------------------------
// Merchants
// ---------------------------------------------------------------------------

export interface MerchantListItem {
  merchant_id: string
  archetype: string
  business_tier: string
  signup_date: string
}

export interface MerchantListResponse {
  count: number
  merchants: MerchantListItem[]
}

export interface BenchmarkHistory {
  first_date: string
  last_date: string
  n_days: number
}

export interface LatestObservedSnapshot {
  as_of_date: string
  day_index: number
  gmv: number
  transaction_count: number
  chargeback_rate: number
  refund_rate: number
  fulfillment_on_time_rate: number
  liquidity_balance: number
  provenance: Provenance
}

export interface MerchantProfileResponse {
  merchant_id: string
  archetype: string
  business_tier: string
  signup_date: string
  weekly_seasonality_profile: string
  benchmark_history: BenchmarkHistory
  latest_observed_snapshot: LatestObservedSnapshot
}

export interface ObservationRecord {
  date: string
  day_index: number
  gmv: number
  transaction_count: number
  aov: number
  refund_count: number
  refund_amount: number
  refund_rate: number
  chargeback_count: number
  chargeback_amount: number
  chargeback_rate: number
  fulfillment_delay_avg_days: number
  fulfillment_on_time_rate: number
  customer_count: number
  new_customers: number
  returning_customers: number
  new_customer_rate: number
  pct_pay_card: number
  pct_pay_upi: number
  pct_pay_netbanking: number
  pct_pay_wallet: number
  pct_pay_bnpl: number
  liquidity_balance: number
  pending_settlement_amount: number
}

export interface ObservationsResponse {
  merchant_id: string
  count: number
  observations: ObservationRecord[]
}

// ---------------------------------------------------------------------------
// Risk
// ---------------------------------------------------------------------------

export interface ModelSection {
  artifact_id: string
  probability_calibrated: number
  probability_raw_rf: number
  decision_threshold: number
  risk_state: 'elevated' | 'normal'
  provenance: Provenance
  disclaimer: string
}

export interface ExposureEstimate {
  value: number
  provenance: Provenance
  method: string
  note: string
}

export interface RetrospectiveActual {
  value: number | null
  available: boolean
  provenance: Provenance
  note: string
}

export interface ExposureSection {
  estimate: ExposureEstimate
  retrospective_actual: RetrospectiveActual
}

export interface AvailableLiquidity {
  value: number
  provenance: Provenance
  note: string
}

export interface LiquidityStress {
  value: number | null
  provenance: Provenance
  note: string
  formula?: string | null
}

export interface LiquiditySection {
  available_liquidity: AvailableLiquidity
  liquidity_stress: LiquidityStress
}

export interface RiskResponse {
  merchant_id: string
  as_of_date: string
  day_index: number
  horizon_days: number
  model: ModelSection
  exposure: ExposureSection
  liquidity: LiquiditySection
}

// ---------------------------------------------------------------------------
// Explainability
// ---------------------------------------------------------------------------

export type DriverDirection = 'increases_risk' | 'decreases_risk' | 'neutral'

export interface Driver {
  feature: string
  group: string
  definition: string
  window: string | null
  kind: string
  value: number
  shap_value: number
  direction: DriverDirection
}

export interface PredictionInfo {
  model_probability_calibrated: number
  model_probability_raw_rf: number
  decision_threshold: number
  predicted_positive: boolean
  note: string
}

export interface FaithfulnessInfo {
  shap_base_value: number
  shap_reconstructed_probability: number
  reconstruction_error: number
  faithful: boolean
}

export interface DriversSection {
  top_positive_contributors: Driver[]
  top_negative_contributors: Driver[]
}

export interface ExplanationResponse {
  merchant_id: string
  as_of_date: string
  day_index: number
  horizon_days: number
  prediction: PredictionInfo
  faithfulness: FaithfulnessInfo
  drivers: DriversSection
  all_contributors: Driver[]
  causality_disclaimer: string
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  detail: string
}
