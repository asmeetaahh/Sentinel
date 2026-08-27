/**
 * Realistic mock API response fixtures for component tests — shaped
 * exactly like backend/api/schemas/*.py, but the VALUES are arbitrary
 * test fixtures, never asserted-against as if they were real benchmark
 * numbers. Production code must never import this file.
 */

import type {
  AssistantResponse,
  ControlsListResponse,
  ExplanationResponse,
  IncidentDetail,
  IncidentListResponse,
  InterventionMemoryListResponse,
  InterventionRecommendationsResponse,
  MerchantListResponse,
  MerchantProfileResponse,
  ObservationsResponse,
  RiskResponse,
  SimulationResponse,
} from '@/api/types'

export const mockMerchantList: MerchantListResponse = {
  count: 2,
  merchants: [
    { merchant_id: 'M0001', archetype: 'SaaS', business_tier: 'mid', signup_date: '2022-01-01' },
    { merchant_id: 'M0002', archetype: 'Travel', business_tier: 'large', signup_date: '2021-06-15' },
  ],
}

export const mockMerchantProfile: MerchantProfileResponse = {
  merchant_id: 'M0001',
  archetype: 'SaaS',
  business_tier: 'mid',
  signup_date: '2022-01-01',
  weekly_seasonality_profile: 'weekday_heavy',
  benchmark_history: { first_date: '2024-01-01', last_date: '2024-06-28', n_days: 180 },
  latest_observed_snapshot: {
    as_of_date: '2024-06-28',
    day_index: 179,
    gmv: 12345.6,
    transaction_count: 42,
    chargeback_rate: 0.01,
    refund_rate: 0.02,
    fulfillment_on_time_rate: 0.95,
    liquidity_balance: 98765.4,
    provenance: 'observed',
  },
}

export const mockRisk: RiskResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  day_index: 179,
  horizon_days: 30,
  model: {
    artifact_id: 'random_forest_calibrated_30d',
    probability_calibrated: 0.42,
    probability_raw_rf: 0.5,
    decision_threshold: 0.6418,
    risk_state: 'normal',
    provenance: 'modeled',
    disclaimer: 'This is a synthetic-benchmark model output, not a validated real-world probability.',
  },
  exposure: {
    estimate: {
      value: 1500,
      provenance: 'derived',
      method: 'trailing 28-day mean daily chargeback_amount extrapolated flat across the 30-day horizon',
      note: 'Deterministic extrapolation from observed data, not an ML prediction.',
    },
    retrospective_actual: {
      value: null,
      available: false,
      provenance: 'observed',
      note: 'Not available: this prediction date is too close to the end of the benchmark.',
    },
  },
  liquidity: {
    available_liquidity: { value: 98765.4, provenance: 'observed', note: 'Same-day liquidity_balance.' },
    liquidity_stress: {
      value: 0.0152,
      provenance: 'derived',
      note: 'Transparent derived ratio, not an ML prediction.',
      formula: 'predicted_chargeback_exposure / available_merchant_liquidity',
    },
  },
}

export const mockExplanation: ExplanationResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  day_index: 179,
  horizon_days: 30,
  prediction: {
    model_probability_calibrated: 0.42,
    model_probability_raw_rf: 0.5,
    decision_threshold: 0.6418,
    predicted_positive: false,
    note: 'SHAP explains model_probability_raw_rf.',
  },
  faithfulness: {
    shap_base_value: 0.5,
    shap_reconstructed_probability: 0.5,
    reconstruction_error: 1e-15,
    faithful: true,
  },
  drivers: {
    top_positive_contributors: [
      {
        feature: 'chargeback_rate_28d',
        group: 'chargeback_behavior',
        definition: 'Volume-weighted chargeback rate over trailing 28d.',
        window: '28d',
        kind: 'level',
        value: 0.02,
        shap_value: 0.08,
        direction: 'increases_risk',
      },
    ],
    top_negative_contributors: [
      {
        feature: 'refund_rate_60d',
        group: 'refund_behavior',
        definition: 'Volume-weighted refund rate over trailing 60d.',
        window: '60d',
        kind: 'level',
        value: 0.01,
        shap_value: -0.03,
        direction: 'decreases_risk',
      },
    ],
  },
  all_contributors: [],
  causality_disclaimer: 'SHAP attributes the model output to its inputs; it does not establish causality.',
}

export const mockControlsList: ControlsListResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  day_index: 179,
  controls: [
    {
      control_id: 'refund_rate_28d',
      label: 'Refund rate (trailing 28 days)',
      feature: 'refund_rate_28d',
      group: 'refund_behavior',
      unit: 'rate_0_to_1',
      description: 'Volume-weighted share of transactions refunded over a trailing 28-day window.',
      min_value: 0,
      max_value: 1,
      baseline_value: 0.1,
    },
    {
      control_id: 'fulfillment_on_time_rate_28d',
      label: 'On-time fulfillment rate (trailing 28 days)',
      feature: 'fulfillment_on_time_rate_28d',
      group: 'fulfillment',
      unit: 'rate_0_to_1',
      description: 'Transaction-volume-weighted mean on-time fulfillment rate over a trailing 28-day window.',
      min_value: 0.41,
      max_value: 0.999,
      baseline_value: 0.9,
    },
    {
      control_id: 'new_customer_rate_28d',
      label: 'New-customer share (trailing 28 days)',
      feature: 'new_customer_rate_28d',
      group: 'customer_mix',
      unit: 'rate_0_to_1',
      description: 'Volume-weighted share of transactions from new customers over a trailing 28-day window.',
      min_value: 0,
      max_value: 0.93,
      baseline_value: 0.55,
    },
  ],
}

export const mockSimulationResponse: SimulationResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  day_index: 179,
  horizon_days: 30,
  controls: [
    {
      control_id: 'refund_rate_28d',
      label: 'Refund rate (trailing 28 days)',
      feature: 'refund_rate_28d',
      group: 'refund_behavior',
      min_value: 0,
      max_value: 1,
      baseline_value: 0.1,
      simulated_value: 0.5,
    },
  ],
  current: {
    probability_calibrated: 0.2,
    probability_raw_rf: 0.25,
    risk_state: 'normal',
    decision_threshold: 0.6418,
    provenance: 'modeled',
  },
  simulated: {
    probability_calibrated: 0.35,
    probability_raw_rf: 0.4,
    risk_state: 'normal',
    decision_threshold: 0.6418,
    provenance: 'modeled',
  },
  probability_delta: { absolute: 0.15, relative: 0.75 },
  exposure: {
    current: { value: 1000, provenance: 'derived', method: 'trailing 28-day mean daily chargeback_amount baseline.' },
    simulated: { value: 1750, provenance: 'derived', method: 'Illustrative scaling by the modeled probability ratio.' },
    delta: { absolute: 750, relative: 0.75 },
  },
  liquidity_stress: {
    current: {
      value: 0.02,
      provenance: 'derived',
      note: 'Transparent derived ratio.',
      formula: 'predicted_chargeback_exposure / available_merchant_liquidity',
    },
    simulated: {
      value: 0.035,
      provenance: 'derived',
      note: 'Transparent derived ratio.',
      formula: 'predicted_chargeback_exposure / available_merchant_liquidity',
    },
    delta: { absolute: 0.015, relative: 0.75 },
  },
  modeled_impact_disclaimer:
    'This is a MODELED IMPACT, not a guaranteed or causal outcome. It does not establish that any control causes a change in real-world risk.',
}

export const mockObservations: ObservationsResponse = {
  merchant_id: 'M0001',
  count: 3,
  observations: [1, 2, 3].map((day) => ({
    date: `2024-06-2${day}`,
    day_index: 170 + day,
    gmv: 10000 + day * 100,
    transaction_count: 30 + day,
    aov: 300,
    refund_count: 1,
    refund_amount: 300,
    refund_rate: 0.03,
    chargeback_count: 0,
    chargeback_amount: 0,
    chargeback_rate: 0,
    fulfillment_delay_avg_days: 1.2,
    fulfillment_on_time_rate: 0.94,
    customer_count: 30,
    new_customers: 10,
    returning_customers: 20,
    new_customer_rate: 0.33,
    pct_pay_card: 0.4,
    pct_pay_upi: 0.3,
    pct_pay_netbanking: 0.1,
    pct_pay_wallet: 0.1,
    pct_pay_bnpl: 0.1,
    liquidity_balance: 90000,
    pending_settlement_amount: 15000,
  })),
}

export const mockIncidentList: IncidentListResponse = {
  merchant_id: 'M0001',
  count: 2,
  incidents: [
    {
      incident_id: 'INC-E0001000',
      merchant_id: 'M0001',
      event_type: 'fulfillment_degradation',
      status: 'resolved',
      priority: 'high',
      horizon_days: 30,
      window: { start_date: '2024-02-21', end_date: '2024-04-05', recovery_end_date: '2024-04-23', duration_days: 44 },
      detected_date: '2024-02-21',
      probability_calibrated: 0.72,
      risk_state: 'elevated',
      exposure_estimate: 4200,
      liquidity_stress: 1.2,
      reason_code: 'GOODS_OR_SERVICE_NOT_RECEIVED',
      reason_code_label: 'Goods or service not received',
      evidence_readiness_status: 'partial',
      estimated_case_count: 8,
      workflow_stage: 'evidence_check',
    },
    {
      incident_id: 'INC-E0001001',
      merchant_id: 'M0001',
      event_type: 'refund_shock',
      status: 'active',
      priority: 'low',
      horizon_days: 30,
      window: { start_date: '2024-05-01', end_date: '2024-05-06', recovery_end_date: '2024-05-18', duration_days: 5 },
      detected_date: '2024-05-01',
      probability_calibrated: 0.65,
      risk_state: 'elevated',
      exposure_estimate: 900,
      liquidity_stress: 0.02,
      reason_code: 'CREDIT_NOT_PROCESSED',
      reason_code_label: 'Credit not processed',
      evidence_readiness_status: 'ready',
      estimated_case_count: 2,
      workflow_stage: 'response_ready_for_merchant_review',
    },
  ],
}

export const mockIncidentDetail: IncidentDetail = {
  incident_id: 'INC-E0001000',
  merchant_id: 'M0001',
  event_type: 'fulfillment_degradation',
  status: 'resolved',
  priority: 'high',
  priority_reasons: [
    "Required evidence for this incident's reason code is incomplete.",
    "8 chargeback occurrences were recorded during this incident's window.",
  ],
  horizon_days: 30,
  day_index: 51,
  window: { start_date: '2024-02-21', end_date: '2024-04-05', recovery_end_date: '2024-04-23', duration_days: 44 },
  detected_date: '2024-02-21',
  detection_note: "The first day within this episode's window on which the existing saved model's calibrated probability reached its own decision threshold.",
  model: mockRisk.model,
  exposure: mockRisk.exposure,
  liquidity: mockRisk.liquidity,
  drivers: mockExplanation.drivers,
  causality_disclaimer: mockExplanation.causality_disclaimer,
  reason_code: {
    code: 'GOODS_OR_SERVICE_NOT_RECEIVED',
    label: 'Goods or service not received',
    description: 'Associated with a synthetic fulfillment-degradation episode.',
    taxonomy_disclaimer: "SENTINEL SYNTHETIC PROTOTYPE TAXONOMY — not Razorpay's proprietary reason-code taxonomy.",
  },
  case_summary: {
    estimated_case_count: 8,
    method: "Sum of observed chargeback_count over the incident's benchmark window.",
    provenance: 'derived',
    note: 'This benchmark contains only daily aggregate observations, not individual transaction-level dispute records.',
  },
  evidence_readiness: {
    reason_code: 'GOODS_OR_SERVICE_NOT_RECEIVED',
    required_evidence: ['invoice', 'payment_confirmation', 'delivery_proof', 'tracking_information'],
    items: [
      {
        category: 'invoice',
        label: 'Invoice',
        required: true,
        available: true,
        rationale: 'Prototype assumption: an invoice/receipt is treated as always available.',
        provenance: 'synthetic_prototype',
      },
      {
        category: 'payment_confirmation',
        label: 'Payment confirmation',
        required: true,
        available: true,
        rationale: 'Prototype assumption: a payment confirmation is treated as always available.',
        provenance: 'synthetic_prototype',
      },
      {
        category: 'delivery_proof',
        label: 'Delivery proof',
        required: true,
        available: false,
        rationale: "Derived from this merchant's observed on-time fulfillment rate during the incident window (42%), below the 70% completeness assumption.",
        provenance: 'derived',
      },
      {
        category: 'tracking_information',
        label: 'Tracking information',
        required: true,
        available: false,
        rationale: "Derived from this merchant's observed on-time fulfillment rate during the incident window (42%), below the 70% completeness assumption.",
        provenance: 'derived',
      },
    ],
    required_count: 4,
    available_count: 2,
    missing_evidence: ['delivery_proof', 'tracking_information'],
    readiness_status: 'partial',
    disclaimer: 'Evidence availability shown here is derived from observed benchmark signals or explicitly documented prototype assumptions — never a real document, tracking number, invoice, or message.',
  },
  scenario_context: {
    event_id: 'E0001000',
    shape: 'gradual',
    severity_score: 0.65,
    affects: ['fulfillment_on_time_rate', 'fulfillment_delay_avg_days', 'chargeback_rate'],
    provenance: 'synthetic_prototype',
    note: "This is the synthetic benchmark generator's own ground-truth scenario parameter.",
  },
  workflow_stage: 'evidence_check',
}

export const mockAssistantResponse: AssistantResponse = {
  merchant_id: 'M0001',
  answer:
    '(Mock assistant response — for local development and testing, not a real AI-generated answer.) As of 2024-06-28, ' +
    "the modeled 30-day probability is 42.0%, which the model classifies as 'normal' against its decision threshold of 64.2%.",
  cited_context: {
    merchant: { merchant_id: 'M0001', archetype: 'SaaS', business_tier: 'mid', signup_date: '2022-01-01', provenance: 'observed' },
    observed_state: {
      as_of_date: '2024-06-28',
      gmv: 12345.6,
      transaction_count: 42,
      chargeback_rate: 0.01,
      refund_rate: 0.02,
      fulfillment_on_time_rate: 0.95,
      provenance: 'observed',
    },
    risk: {
      as_of_date: '2024-06-28',
      horizon_days: 30,
      probability_calibrated: 0.42,
      risk_state: 'normal',
      decision_threshold: 0.6418,
      disclaimer: 'This is a synthetic-benchmark model output, not a validated real-world probability.',
      provenance: 'modeled',
    },
    exposure: { value: 1500, method: 'trailing 28-day mean daily chargeback_amount baseline.', provenance: 'derived' },
    liquidity: { available_liquidity: 98765.4, liquidity_stress: 0.0152, note: 'Transparent derived ratio.', provenance: 'derived' },
    drivers: [
      {
        feature: 'chargeback_rate_28d',
        group: 'chargeback_behavior',
        definition: 'Volume-weighted chargeback rate over trailing 28d.',
        window: '28d',
        kind: 'level',
        value: 0.02,
        shap_value: 0.08,
        direction: 'increases_risk',
      },
    ],
    interventions: [],
    simulation: null,
    incident: null,
    standing_limitations: [
      'Sentinel is a synthetic-benchmark research prototype. It has no access to real Razorpay systems, proprietary data, settlement decisions, or enforcement decisions.',
      'The modeled probability is a synthetic-benchmark model output, not a validated real-world probability.',
    ],
  },
  provenance: { merchant: 'observed', observed_state: 'observed', risk: 'modeled', exposure: 'derived', liquidity: 'derived', drivers: 'modeled' },
  limitations: [
    'Sentinel is a synthetic-benchmark research prototype. It has no access to real Razorpay systems, proprietary data, settlement decisions, or enforcement decisions.',
    'The modeled probability is a synthetic-benchmark model output, not a validated real-world probability.',
  ],
  disclaimer:
    "Sentinel's assistant explains verified model, exposure, liquidity, simulator, and incident outputs that were already computed by deterministic backend services.",
  suggested_next_actions: ['Why is my risk elevated?', 'What does this mean for liquidity?'],
  provider: 'mock',
  guardrail_triggered: false,
}

export const mockEmptyInterventions: InterventionRecommendationsResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  relevance_threshold_z: 2.0,
  count: 0,
  recommendations: [],
  empty_state_note:
    'No intervention is currently justified: none of the three bounded simulator controls show a material deviation from this merchant\'s own recent baseline as of this date.',
}

export const mockInterventionRecommendation = {
  intervention_id: 'M0001:refund_rate_28d:2024-06-28',
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  control_id: 'refund_rate_28d',
  title: 'Review refund pressure',
  reason: "Refund rate (trailing 28 days) is currently 28.0%, which is 2.4 standard deviations above this merchant's own recent historical baseline.",
  priority: 'high' as const,
  priority_rank: 1,
  current_value: { value: 0.28, provenance: 'observed' as const },
  deviation_z: {
    value: 2.4,
    provenance: 'derived' as const,
    method: 'refund_rate_deviation_z — the existing causal feature-engineering deviation-from-baseline z-score.',
  },
  shap_corroboration: {
    corroborated: true,
    provenance: 'modeled' as const,
    note: "Whether any feature in this control's behavior group currently appears among this merchant's verified SHAP contributors pushing risk higher.",
  },
  simulator_control: {
    control_id: 'refund_rate_28d',
    label: 'Refund rate (trailing 28 days)',
    feature: 'refund_rate_28d',
    group: 'refund_behavior',
    unit: 'rate_0_to_1',
    description: 'Volume-weighted share of transactions refunded over a trailing 28-day window.',
    min_value: 0,
    max_value: 1,
    baseline_value: 0.28,
  },
  modeled_impact_reminder:
    'This is an observed deviation from the merchant\'s own recent baseline — not a claim that changing it will reduce real-world risk. Test the modeled impact of adjusting this control in the simulator.',
}

export const mockInterventionsWithRecommendation: InterventionRecommendationsResponse = {
  merchant_id: 'M0001',
  as_of_date: '2024-06-28',
  relevance_threshold_z: 2.0,
  count: 1,
  recommendations: [mockInterventionRecommendation],
  empty_state_note: null,
}

export const mockEmptyInterventionMemory: InterventionMemoryListResponse = {
  merchant_id: 'M0001',
  count: 0,
  records: [],
  empty_state_note: 'No intervention activity has been recorded for this merchant in this session. Recording is entirely optional and merchant-initiated — nothing is recorded automatically.',
}

export const mockInterventionMemoryRecord = {
  intervention_id: 'M0001:refund_rate_28d:2024-06-28',
  merchant_id: 'M0001',
  control_id: 'refund_rate_28d',
  recommendation_title: 'Review refund pressure',
  action_status: 'acknowledged' as const,
  timestamp: '2026-08-27T14:39:24.481251Z',
  simulated_impact: null,
  outcome_status: 'not_observed' as const,
  outcome_note:
    "This synthetic benchmark does not provide real-world post-intervention outcomes. Sentinel does not fabricate, infer, or claim to have observed one — this record remains 'not_observed' until a legitimate outcome data source exists.",
}

export const mockInterventionMemoryWithRecords: InterventionMemoryListResponse = {
  merchant_id: 'M0001',
  count: 1,
  records: [mockInterventionMemoryRecord],
  empty_state_note: null,
}
