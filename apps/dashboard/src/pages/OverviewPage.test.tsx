import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OverviewPage } from './OverviewPage'
import { MerchantSelector } from '@/components/common/MerchantSelector'
import { MerchantProvider } from '@/context/MerchantContext'
import * as endpoints from '@/api/endpoints'
import {
  mockDataQualityLimited,
  mockDataQualityMedium,
  mockEmptyInterventionMemory,
  mockEmptyInterventions,
  mockExplanation,
  mockInterventionMemoryWithRecords,
  mockInterventionsWithRecommendation,
  mockMerchantList,
  mockMerchantProfile,
  mockObservations,
  mockRisk,
} from '@/test/fixtures'

function renderOverview() {
  return render(
    <MemoryRouter>
      <MerchantProvider>
        <OverviewPage />
      </MerchantProvider>
    </MemoryRouter>,
  )
}

function renderOverviewWithSelector() {
  return render(
    <MemoryRouter>
      <MerchantProvider>
        <MerchantSelector />
        <OverviewPage />
      </MerchantProvider>
    </MemoryRouter>,
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
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockEmptyInterventions)
    vi.spyOn(endpoints, 'getInterventionMemory').mockResolvedValue(mockEmptyInterventionMemory)
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

    // Confidence / Data Quality surface, from the same risk response
    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
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

  // ---------------------------------------------------------------------
  // Confidence / Data Quality
  // ---------------------------------------------------------------------

  it('renders medium confidence with its real reason text when expanded', async () => {
    vi.spyOn(endpoints, 'getRisk').mockResolvedValue({ ...mockRisk, data_quality: mockDataQualityMedium })
    renderOverview()

    expect(await screen.findByText('Medium')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Why this level'))
    expect(screen.getByText(mockDataQualityMedium.reasons[0])).toBeInTheDocument()
    expect(screen.getByText(mockDataQualityMedium.limitations[0])).toBeInTheDocument()
  })

  it('renders limited confidence honestly, with its real limited-history reason', async () => {
    vi.spyOn(endpoints, 'getRisk').mockResolvedValue({ ...mockRisk, data_quality: mockDataQualityLimited })
    renderOverview()

    expect(await screen.findByText('Limited')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Why this level'))
    expect(screen.getByText(mockDataQualityLimited.reasons[0])).toBeInTheDocument()
  })

  it('never renders a fabricated numeric or percentage confidence score', async () => {
    renderOverview()
    await screen.findByText('Confidence')
    await userEvent.click(screen.getByText('Why this level'))
    expect(screen.queryByText(/\d+%\s*confiden/i)).not.toBeInTheDocument()
  })

  // ---------------------------------------------------------------------
  // Intervention Intelligence + Risk Memory
  // ---------------------------------------------------------------------

  it('shows the honest empty state when no intervention is justified', async () => {
    renderOverview()
    expect(await screen.findByText('No intervention currently justified')).toBeInTheDocument()
    expect(screen.getByText(mockEmptyInterventions.empty_state_note as string)).toBeInTheDocument()
  })

  it('renders a real recommendation with priority and reason text from the API', async () => {
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockInterventionsWithRecommendation)
    renderOverview()

    expect(await screen.findByText('Review refund pressure')).toBeInTheDocument()
    expect(screen.getByText('High priority')).toBeInTheDocument()
    expect(screen.getByText(mockInterventionsWithRecommendation.recommendations[0].reason)).toBeInTheDocument()
    expect(screen.getByText('Verified SHAP driver')).toBeInTheDocument()
  })

  it('the "Test in Simulator" action links to the simulator with the control identified', async () => {
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockInterventionsWithRecommendation)
    renderOverview()

    const link = await screen.findByRole('link', { name: /test in simulator/i })
    expect(link).toHaveAttribute('href', '/simulator?control=refund_rate_28d')
  })

  it('shows an empty Risk Memory state honestly, with no fabricated history', async () => {
    renderOverview()
    expect(await screen.findByText('No intervention activity recorded yet')).toBeInTheDocument()
  })

  it('renders a real memory record distinguishing action status from the always-not-observed outcome', async () => {
    vi.spyOn(endpoints, 'getInterventionMemory').mockResolvedValue(mockInterventionMemoryWithRecords)
    renderOverview()

    expect(await screen.findByText('Acknowledged')).toBeInTheDocument()
    expect(screen.getByText('Outcome: Not observed')).toBeInTheDocument()
    expect(screen.getByText(mockInterventionMemoryWithRecords.records[0].outcome_note)).toBeInTheDocument()
  })

  it('acknowledging a recommendation records it and refreshes Risk Memory', async () => {
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockInterventionsWithRecommendation)
    const recordSpy = vi.spyOn(endpoints, 'recordIntervention').mockResolvedValue({
      ...mockInterventionsWithRecommendation.recommendations[0],
      recommendation_title: 'Review refund pressure',
      action_status: 'acknowledged',
      timestamp: '2026-08-27T00:00:00Z',
      simulated_impact: null,
      outcome_status: 'not_observed',
      outcome_note: 'not observed',
    } as never)

    renderOverview()
    const button = await screen.findByRole('button', { name: /^acknowledge$/i })
    await userEvent.click(button)

    await waitFor(() =>
      expect(recordSpy).toHaveBeenCalledWith(
        'M0001',
        expect.objectContaining({ intervention_id: mockInterventionsWithRecommendation.recommendations[0].intervention_id, action_status: 'acknowledged' }),
      ),
    )
    expect(await screen.findByText('Acknowledged ✓')).toBeInTheDocument()
    // Memory list is refetched after recording.
    expect(endpoints.getInterventionMemory).toHaveBeenCalledTimes(2)
  })

  it('never renders any recommendation text not returned by the API', async () => {
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockInterventionsWithRecommendation)
    renderOverview()
    await screen.findByText('Review refund pressure')

    expect(screen.queryByText(/guaranteed/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/will reduce/i)).not.toBeInTheDocument()
  })

  it('switching merchants refetches interventions and Risk Memory for the new merchant and drops the previous merchant\'s data', async () => {
    vi.spyOn(endpoints, 'getMerchantProfile').mockImplementation((merchantId: string) =>
      Promise.resolve({ ...mockMerchantProfile, merchant_id: merchantId, archetype: merchantId === 'M0002' ? 'Travel' : 'SaaS' }),
    )
    vi.spyOn(endpoints, 'getRisk').mockImplementation((merchantId: string) =>
      Promise.resolve({ ...mockRisk, merchant_id: merchantId, data_quality: merchantId === 'M0002' ? mockDataQualityLimited : mockRisk.data_quality }),
    )
    vi.spyOn(endpoints, 'getInterventions').mockImplementation((merchantId: string) =>
      Promise.resolve(
        merchantId === 'M0002'
          ? mockInterventionsWithRecommendation
          : mockEmptyInterventions,
      ),
    )
    vi.spyOn(endpoints, 'getInterventionMemory').mockImplementation((merchantId: string) =>
      Promise.resolve(merchantId === 'M0002' ? mockInterventionMemoryWithRecords : mockEmptyInterventionMemory),
    )

    renderOverviewWithSelector()

    // M0001 is selected by default: no recommendation, empty Risk Memory, high confidence.
    expect(await screen.findByText('No intervention currently justified')).toBeInTheDocument()
    expect(screen.getByText('No intervention activity recorded yet')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(endpoints.getInterventions).toHaveBeenCalledWith('M0001', expect.anything())

    await userEvent.selectOptions(screen.getByLabelText('Merchant'), 'M0002')

    // M0002's real data appears (in both the recommendation row and the Risk Memory record)...
    expect(await screen.findAllByText('Review refund pressure')).toHaveLength(2)
    expect(await screen.findByText('Acknowledged')).toBeInTheDocument()
    await waitFor(() => expect(endpoints.getInterventions).toHaveBeenCalledWith('M0002', expect.anything()))
    expect(endpoints.getInterventionMemory).toHaveBeenCalledWith('M0002')

    // ...and M0001's stale empty-state text and confidence level are gone, not just supplemented.
    expect(screen.queryByText('No intervention currently justified')).not.toBeInTheDocument()
    expect(screen.queryByText('No intervention activity recorded yet')).not.toBeInTheDocument()
    expect(await screen.findByText('Limited')).toBeInTheDocument()
    expect(screen.queryByText('High')).not.toBeInTheDocument()
  })
})
