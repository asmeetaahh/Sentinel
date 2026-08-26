/**
 * Realistic mock API response fixtures for component tests — shaped
 * exactly like backend/api/schemas/*.py, but the VALUES are arbitrary
 * test fixtures, never asserted-against as if they were real benchmark
 * numbers. Production code must never import this file.
 */

import type {
  ControlsListResponse,
  ExplanationResponse,
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
