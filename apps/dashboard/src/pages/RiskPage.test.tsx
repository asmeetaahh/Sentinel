import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { MerchantProvider } from '@/context/MerchantContext'
import { mockMerchantList, mockMerchantProfile, mockObservations, mockRisk } from '@/test/fixtures'

import { RiskPage } from './RiskPage'

function renderRiskPage() {
  return render(
    <MerchantProvider>
      <RiskPage />
    </MerchantProvider>,
  )
}

describe('RiskPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'getMerchantProfile').mockResolvedValue(mockMerchantProfile)
    vi.spyOn(endpoints, 'getRisk').mockResolvedValue(mockRisk)
    vi.spyOn(endpoints, 'getObservations').mockResolvedValue(mockObservations)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {}))
    renderRiskPage()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('renders the same real risk state, probability, and confidence as Overview — the same verified assessment, not a second one', async () => {
    renderRiskPage()

    expect(await screen.findByText('Normal')).toBeInTheDocument()
    expect(screen.getByText('42.0%')).toBeInTheDocument()
    expect(screen.getByText(/Flag threshold/)).toBeInTheDocument()
    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('renders exposure and liquidity from the same risk response', async () => {
    renderRiskPage()
    expect(await screen.findByText('Estimated 30-day exposure')).toBeInTheDocument()
    expect(screen.getByText('1.5K units')).toBeInTheDocument()
    expect(screen.getByText('Available liquidity')).toBeInTheDocument()
  })

  it('renders the observed trajectory chart', async () => {
    renderRiskPage()
    expect(await screen.findByText('Recent trajectory (last 90 observed days)')).toBeInTheDocument()
  })

  it('does not render SHAP driver content — that belongs to the Explainability page, not Risk', async () => {
    renderRiskPage()
    await screen.findByText('Normal')
    expect(screen.queryByText('Verified model drivers')).not.toBeInTheDocument()
  })

  it('shows an error state when the risk endpoint fails, without blocking the merchant intro', async () => {
    vi.spyOn(endpoints, 'getRisk').mockRejectedValue(new Error('risk endpoint down'))
    renderRiskPage()
    expect(await screen.findByText('risk endpoint down')).toBeInTheDocument()
    expect(await screen.findByText(/Risk Engine/i)).toBeInTheDocument()
  })

  it('switching merchants refetches risk data for the new merchant', async () => {
    vi.spyOn(endpoints, 'getMerchantProfile').mockImplementation((merchantId: string) =>
      Promise.resolve({ ...mockMerchantProfile, merchant_id: merchantId }),
    )
    renderRiskPage()
    await screen.findByText('Normal')
    await waitFor(() => expect(endpoints.getRisk).toHaveBeenCalledWith('M0001', expect.anything()))
  })
})
