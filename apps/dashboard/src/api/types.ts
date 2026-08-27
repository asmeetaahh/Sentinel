/**
 * TypeScript types mirroring the backend's Pydantic response schemas
 * exactly (see backend/api/schemas/*.py). Keep in sync with the backend —
 * these are not independently invented shapes.
 */

export type Provenance = 'observed' | 'modeled' | 'derived' | 'synthetic_prototype'

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
// Simulator
// ---------------------------------------------------------------------------

export interface ControlMeta {
  control_id: string
  label: string
  feature: string
  group: string
  unit: string
  description: string
  min_value: number
  max_value: number
  baseline_value: number
}

export interface ControlsListResponse {
  merchant_id: string
  as_of_date: string
  day_index: number
  controls: ControlMeta[]
}

/** Exactly the three controls backend/simulation/controls.py exposes — kept
 * in sync with backend/api/schemas/simulation.py's SimulationRequest. */
export interface SimulationRequestBody {
  as_of_date: string
  horizon_days?: number
  refund_rate_28d?: number
  fulfillment_on_time_rate_28d?: number
  new_customer_rate_28d?: number
}

export interface AppliedControl {
  control_id: string
  label: string
  feature: string
  group: string
  min_value: number
  max_value: number
  baseline_value: number
  simulated_value: number
}

export interface SimulationModelOutcome {
  probability_calibrated: number
  probability_raw_rf: number
  risk_state: 'elevated' | 'normal'
  decision_threshold: number
  provenance: Provenance
}

export interface Delta {
  absolute: number
  relative: number | null
}

export interface SimulationExposureValue {
  value: number
  provenance: Provenance
  method: string
}

export interface SimulationExposureSection {
  current: SimulationExposureValue
  simulated: SimulationExposureValue
  delta: Delta
}

export interface SimulationLiquidityStressValue {
  value: number | null
  provenance: Provenance
  note: string
  formula?: string | null
}

export interface SimulationLiquidityStressSection {
  current: SimulationLiquidityStressValue
  simulated: SimulationLiquidityStressValue
  delta: Delta | null
}

export interface SimulationResponse {
  merchant_id: string
  as_of_date: string
  day_index: number
  horizon_days: number
  controls: AppliedControl[]
  current: SimulationModelOutcome
  simulated: SimulationModelOutcome
  probability_delta: Delta
  exposure: SimulationExposureSection
  liquidity_stress: SimulationLiquidityStressSection
  modeled_impact_disclaimer: string
}

// ---------------------------------------------------------------------------
// Incidents / Evidence Readiness
// ---------------------------------------------------------------------------

export type IncidentPriority = 'high' | 'medium' | 'low'
export type IncidentStatus = 'active' | 'resolved'
export type EvidenceReadinessStatus = 'ready' | 'partial' | 'insufficient'
export type WorkflowStage = 'evidence_check' | 'response_ready_for_merchant_review'

export interface IncidentWindow {
  start_date: string
  end_date: string
  recovery_end_date: string
  duration_days: number
}

export interface ReasonCodeInfo {
  code: string
  label: string
  description: string
  taxonomy_disclaimer: string
}

export interface CaseSummary {
  estimated_case_count: number
  method: string
  provenance: Provenance
  note: string
}

export interface EvidenceItem {
  category: string
  label: string
  required: boolean
  available: boolean
  rationale: string
  provenance: Provenance
}

export interface EvidenceReadiness {
  reason_code: string
  required_evidence: string[]
  items: EvidenceItem[]
  required_count: number
  available_count: number
  missing_evidence: string[]
  readiness_status: EvidenceReadinessStatus
  disclaimer: string
}

export interface ScenarioContext {
  event_id: string
  shape: string
  severity_score: number
  affects: string[]
  provenance: Provenance
  note: string
}

export interface IncidentSummary {
  incident_id: string
  merchant_id: string
  event_type: string
  status: IncidentStatus
  priority: IncidentPriority
  horizon_days: number
  window: IncidentWindow
  detected_date: string
  probability_calibrated: number
  risk_state: 'elevated' | 'normal'
  exposure_estimate: number
  liquidity_stress: number | null
  reason_code: string
  reason_code_label: string
  evidence_readiness_status: EvidenceReadinessStatus
  estimated_case_count: number
  workflow_stage: WorkflowStage
}

export interface IncidentListResponse {
  merchant_id: string
  count: number
  incidents: IncidentSummary[]
}

export interface IncidentDetail {
  incident_id: string
  merchant_id: string
  event_type: string
  status: IncidentStatus
  priority: IncidentPriority
  priority_reasons: string[]
  horizon_days: number
  day_index: number
  window: IncidentWindow
  detected_date: string
  detection_note: string
  model: ModelSection
  exposure: ExposureSection
  liquidity: LiquiditySection
  drivers: DriversSection
  causality_disclaimer: string
  reason_code: ReasonCodeInfo
  case_summary: CaseSummary
  evidence_readiness: EvidenceReadiness
  scenario_context: ScenarioContext
  workflow_stage: WorkflowStage
}

export interface IncidentEvidenceResponse {
  incident_id: string
  merchant_id: string
  evidence_readiness: EvidenceReadiness
}

// ---------------------------------------------------------------------------
// AI Orchestrator
// ---------------------------------------------------------------------------

export interface MerchantAIContext {
  merchant_id: string
  archetype: string
  business_tier: string
  signup_date: string
  provenance: Provenance
}

export interface ObservedStateAIContext {
  as_of_date: string
  gmv: number
  transaction_count: number
  chargeback_rate: number
  refund_rate: number
  fulfillment_on_time_rate: number
  provenance: Provenance
}

export interface RiskAIContext {
  as_of_date: string
  horizon_days: number
  probability_calibrated: number
  risk_state: 'elevated' | 'normal'
  decision_threshold: number
  disclaimer: string
  provenance: Provenance
}

export interface ExposureAIContext {
  value: number
  method: string
  provenance: Provenance
}

export interface LiquidityAIContext {
  available_liquidity: number
  liquidity_stress: number | null
  note: string
  provenance: Provenance
}

export interface SimulationAIContext {
  controls_changed: Record<string, number>
  current_probability: number
  simulated_probability: number
  probability_delta_absolute: number
  exposure_current: number
  exposure_simulated: number
  liquidity_stress_current: number | null
  liquidity_stress_simulated: number | null
  disclaimer: string
  provenance: Provenance
}

export interface IncidentAIContext {
  incident_id: string
  event_type: string
  status: IncidentStatus
  priority: IncidentPriority
  priority_reasons: string[]
  reason_code: string
  reason_code_label: string
  reason_code_taxonomy_disclaimer: string
  evidence_readiness_status: EvidenceReadinessStatus
  missing_evidence: string[]
  estimated_case_count: number
  provenance: Provenance
}

export interface InterventionRecommendationAIContext {
  intervention_id: string
  control_id: string
  title: string
  reason: string
  priority: 'high' | 'medium'
  provenance: Provenance
}

export interface SentinelAIContext {
  merchant: MerchantAIContext
  observed_state: ObservedStateAIContext | null
  risk: RiskAIContext | null
  exposure: ExposureAIContext | null
  liquidity: LiquidityAIContext | null
  drivers: Driver[]
  interventions: InterventionRecommendationAIContext[]
  simulation: SimulationAIContext | null
  incident: IncidentAIContext | null
  standing_limitations: string[]
}

export interface AssistantRequestBody {
  question: string
  as_of_date?: string
  incident_id?: string
  simulation?: SimulationRequestBody
}

export interface AssistantResponse {
  merchant_id: string
  answer: string
  cited_context: SentinelAIContext
  provenance: Record<string, Provenance>
  limitations: string[]
  disclaimer: string
  suggested_next_actions: string[]
  provider: string
  guardrail_triggered: boolean
}

// ---------------------------------------------------------------------------
// Intervention Intelligence / Merchant Risk Memory
// ---------------------------------------------------------------------------

export type InterventionPriority = 'high' | 'medium'
export type ActionStatus = 'reviewed' | 'simulated' | 'acknowledged' | 'dismissed'
export type OutcomeStatus = 'not_observed'

export interface ValueWithProvenance {
  value: number
  provenance: Provenance
}

export interface DeviationInfo {
  value: number
  provenance: Provenance
  method: string
}

export interface ShapCorroboration {
  corroborated: boolean
  provenance: Provenance
  note: string
}

export interface InterventionRecommendation {
  intervention_id: string
  merchant_id: string
  as_of_date: string
  control_id: string
  title: string
  reason: string
  priority: InterventionPriority
  priority_rank: number
  current_value: ValueWithProvenance
  deviation_z: DeviationInfo
  shap_corroboration: ShapCorroboration
  simulator_control: ControlMeta
  modeled_impact_reminder: string
}

export interface InterventionRecommendationsResponse {
  merchant_id: string
  as_of_date: string
  relevance_threshold_z: number
  count: number
  recommendations: InterventionRecommendation[]
  empty_state_note: string | null
}

export interface SimulatedImpactSummary {
  current_probability: number
  simulated_probability: number
  probability_delta_absolute: number
  exposure_current: number
  exposure_simulated: number
  liquidity_stress_current: number | null
  liquidity_stress_simulated: number | null
  disclaimer: string
  provenance: Provenance
}

export interface InterventionMemoryRecord {
  intervention_id: string
  merchant_id: string
  control_id: string
  recommendation_title: string
  action_status: ActionStatus
  timestamp: string
  simulated_impact: SimulatedImpactSummary | null
  outcome_status: OutcomeStatus
  outcome_note: string
}

export interface InterventionMemoryListResponse {
  merchant_id: string
  count: number
  records: InterventionMemoryRecord[]
  empty_state_note: string | null
}

export interface RecordInterventionRequestBody {
  intervention_id: string
  action_status: ActionStatus
  simulation?: SimulationRequestBody
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  detail: string
}
