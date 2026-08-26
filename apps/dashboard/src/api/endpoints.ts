/**
 * One typed function per backend endpoint (backend/api/routers/*.py).
 * Components and hooks call these — never the raw client.
 */

import { apiClient } from './client'
import type {
  ControlsListResponse,
  ExplanationResponse,
  HealthResponse,
  MerchantListResponse,
  MerchantProfileResponse,
  ModelMetadataResponse,
  ObservationsResponse,
  RiskResponse,
  SimulationRequestBody,
  SimulationResponse,
} from './types'

export function getHealth(): Promise<HealthResponse> {
  return apiClient.request('/health')
}

export function getModelMetadata(): Promise<ModelMetadataResponse> {
  return apiClient.request('/metadata')
}

export function listMerchants(archetype?: string): Promise<MerchantListResponse> {
  return apiClient.request('/merchants', { params: { archetype } })
}

export function getMerchantProfile(merchantId: string): Promise<MerchantProfileResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}`)
}

export function getObservations(
  merchantId: string,
  params?: { start_date?: string; end_date?: string; limit?: number },
): Promise<ObservationsResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/observations`, { params })
}

export function getRisk(merchantId: string, asOfDate: string, horizonDays = 30): Promise<RiskResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/risk`, {
    params: { as_of_date: asOfDate, horizon_days: horizonDays },
  })
}

export function getExplanation(merchantId: string, asOfDate: string, topK = 6): Promise<ExplanationResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/explanation`, {
    params: { as_of_date: asOfDate, top_k: topK },
  })
}

export function getSimulationControls(merchantId: string, asOfDate: string): Promise<ControlsListResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/simulation/controls`, {
    params: { as_of_date: asOfDate },
  })
}

export function runSimulation(merchantId: string, body: SimulationRequestBody): Promise<SimulationResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/simulation`, {
    method: 'POST',
    body,
  })
}
