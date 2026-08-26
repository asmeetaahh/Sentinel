import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OverviewPage } from './OverviewPage'
import { MerchantProvider } from '@/context/MerchantContext'
import * as endpoints from '@/api/endpoints'
import { mockExplanation, mockMerchantList, mockMerchantProfile, mockObservations, mockRisk } from '@/test/fixtures'

function renderOverview() {
  return render(
    <MerchantProvider>
      <OverviewPage />
    </MerchantProvider>,
  )
}

describe('OverviewPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'getMerchantProfile').mockResolvedValue(mockMerchantProfile)
    vi.spyOn(endpoints, 'getRisk').mockResolvedValue(mockRisk)
    vi.spyOn(endpoints, 'getExplanation').mockResolvedValue(mockExplanation)
    vi.spyOn(endpoints, 'getObservations').mockResolvedValue(mockObservations)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {})) // never resolves
    renderOverview()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('renders real risk, exposure, liquidity, and driver data returned by the API', async () => {
    renderOverview()

    await waitFor(() => expect(screen.getByText('Normal')).toBeInTheDocument())

    // Risk summary: probability + threshold come straight from the mocked API response
    expect(screen.getByText('42.0%')).toBeInTheDocument()

    // Exposure card
    expect(await screen.findByText('Estimated 30-day exposure')).toBeInTheDocument()
    expect(screen.getByText('1.5K units')).toBeInTheDocument()

    // Liquidity card
    expect(screen.getByText('Available liquidity')).toBeInTheDocument()

    // Risk drivers, from the mocked explanation endpoint
    expect(await screen.findByText(/Chargeback rate 28d/i)).toBeInTheDocument()

    // Provenance labels are all present, distinguishing observed/modeled/derived
    expect(screen.getAllByText('Modeled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Derived').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Observed').length).toBeGreaterThan(0)
  })

  it('shows an error state when the risk endpoint fails, without blocking the rest of the page', async () => {
    vi.spyOn(endpoints, 'getRisk').mockRejectedValue(new Error('risk endpoint down'))
    renderOverview()

    expect(await screen.findByText('risk endpoint down')).toBeInTheDocument()
    // The merchant snapshot section (independent of the risk call) still renders.
    expect(await screen.findByText(/Current merchant state/i)).toBeInTheDocument()
  })

  it('shows an error state when the merchant list fails to load', async () => {
    vi.spyOn(endpoints, 'listMerchants').mockRejectedValue(new Error('backend unreachable'))
    renderOverview()
    expect(await screen.findByText('backend unreachable')).toBeInTheDocument()
  })
})
