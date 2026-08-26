/**
 * One typed function per backend endpoint (backend/api/routers/*.py).
 * Components and hooks call these — never the raw client.
 */

import { apiClient } from './client'
import type {
  ExplanationResponse,
  HealthResponse,
  MerchantListResponse,
  MerchantProfileResponse,
  ModelMetadataResponse,
  ObservationsResponse,
  RiskResponse,
} from './types'

export function getHealth(): Promise<HealthResponse> {
  return apiClient.request('/health')
}

export function getModelMetadata(): Promise<ModelMetadataResponse> {
  return apiClient.request('/metadata')
}

export function listMerchants(archetype?: string): Promise<MerchantListResponse> {
  return apiClient.request('/merchants', { archetype })
}

export function getMerchantProfile(merchantId: string): Promise<MerchantProfileResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}`)
}

export function getObservations(
  merchantId: string,
  params?: { start_date?: string; end_date?: string; limit?: number },
): Promise<ObservationsResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/observations`, params)
}

export function getRisk(merchantId: string, asOfDate: string, horizonDays = 30): Promise<RiskResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/risk`, {
    as_of_date: asOfDate,
    horizon_days: horizonDays,
  })
}

export function getExplanation(merchantId: string, asOfDate: string, topK = 6): Promise<ExplanationResponse> {
  return apiClient.request(`/merchants/${encodeURIComponent(merchantId)}/explanation`, {
    as_of_date: asOfDate,
    top_k: topK,
  })
}
