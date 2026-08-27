import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import type { InterventionRecommendation } from '@/api/types'
import { mockInterventionRecommendation, mockInterventionsWithRecommendation } from '@/test/fixtures'

import { InterventionIntelligence } from './InterventionIntelligence'

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

const lowPriorityRecommendation: InterventionRecommendation = {
  ...mockInterventionRecommendation,
  intervention_id: 'M0001:fulfillment_on_time_rate_28d:2024-06-28',
  control_id: 'fulfillment_on_time_rate_28d',
  title: 'Review fulfillment reliability',
  reason: 'On-time fulfillment rate is currently 82.0%, which is 2.1 standard deviations below baseline.',
  priority: 'medium',
  priority_rank: 2,
  shap_corroboration: { ...mockInterventionRecommendation.shap_corroboration, corroborated: false },
}

describe('InterventionIntelligence', () => {
  it('renders the honest empty state when there are no recommendations', () => {
    renderWithRouter(
      <InterventionIntelligence
        merchantId="M0001"
        interventions={{ merchant_id: 'M0001', as_of_date: '2024-06-28', relevance_threshold_z: 2.0, count: 0, recommendations: [], empty_state_note: 'nothing to see' }}
        onRecorded={vi.fn()}
      />,
    )
    expect(screen.getByText('No intervention currently justified')).toBeInTheDocument()
    expect(screen.getByText('nothing to see')).toBeInTheDocument()
  })

  it('renders recommendations in the order the API already ranked them (high priority first)', () => {
    renderWithRouter(
      <InterventionIntelligence
        merchantId="M0001"
        interventions={{
          merchant_id: 'M0001',
          as_of_date: '2024-06-28',
          relevance_threshold_z: 2.0,
          count: 2,
          recommendations: [mockInterventionRecommendation, lowPriorityRecommendation],
          empty_state_note: null,
        }}
        onRecorded={vi.fn()}
      />,
    )
    const titles = screen.getAllByRole('heading', { level: 4 }).map((el) => el.textContent)
    expect(titles).toEqual(['Review refund pressure', 'Review fulfillment reliability'])
  })

  it('displays priority badges distinctly for high vs. medium', () => {
    renderWithRouter(
      <InterventionIntelligence
        merchantId="M0001"
        interventions={{
          ...mockInterventionsWithRecommendation,
          count: 2,
          recommendations: [mockInterventionRecommendation, lowPriorityRecommendation],
        }}
        onRecorded={vi.fn()}
      />,
    )
    expect(screen.getByText('High priority')).toBeInTheDocument()
    expect(screen.getByText('Medium priority')).toBeInTheDocument()
  })

  it('only shows the "Verified SHAP driver" badge for corroborated recommendations', () => {
    renderWithRouter(
      <InterventionIntelligence
        merchantId="M0001"
        interventions={{
          ...mockInterventionsWithRecommendation,
          count: 2,
          recommendations: [mockInterventionRecommendation, lowPriorityRecommendation],
        }}
        onRecorded={vi.fn()}
      />,
    )
    expect(screen.getAllByText('Verified SHAP driver')).toHaveLength(1)
  })

  it('the "Test in Simulator" link identifies the exact control for each recommendation', () => {
    renderWithRouter(
      <InterventionIntelligence
        merchantId="M0001"
        interventions={{
          ...mockInterventionsWithRecommendation,
          count: 2,
          recommendations: [mockInterventionRecommendation, lowPriorityRecommendation],
        }}
        onRecorded={vi.fn()}
      />,
    )
    const links = screen.getAllByRole('link', { name: /test in simulator/i })
    expect(links[0]).toHaveAttribute('href', '/simulator?control=refund_rate_28d')
    expect(links[1]).toHaveAttribute('href', '/simulator?control=fulfillment_on_time_rate_28d')
  })

  it('acknowledging calls the API with the exact intervention_id and shows a confirmed state', async () => {
    const onRecorded = vi.fn()
    vi.spyOn(endpoints, 'recordIntervention').mockResolvedValue({
      ...mockInterventionRecommendation,
      recommendation_title: mockInterventionRecommendation.title,
      action_status: 'acknowledged',
      timestamp: '2026-08-27T00:00:00Z',
      simulated_impact: null,
      outcome_status: 'not_observed',
      outcome_note: 'not observed',
    } as never)

    renderWithRouter(<InterventionIntelligence merchantId="M0001" interventions={mockInterventionsWithRecommendation} onRecorded={onRecorded} />)
    await userEvent.click(screen.getByRole('button', { name: /^acknowledge$/i }))

    await waitFor(() =>
      expect(endpoints.recordIntervention).toHaveBeenCalledWith('M0001', {
        intervention_id: mockInterventionRecommendation.intervention_id,
        action_status: 'acknowledged',
      }),
    )
    expect(await screen.findByText('Acknowledged ✓')).toBeInTheDocument()
    expect(onRecorded).toHaveBeenCalledTimes(1)
  })

  it('expanding "Why this matters" shows the real deviation method and modeled-impact reminder, never a fabricated claim', async () => {
    renderWithRouter(<InterventionIntelligence merchantId="M0001" interventions={mockInterventionsWithRecommendation} onRecorded={vi.fn()} />)
    await userEvent.click(screen.getByText('Why this matters'))

    expect(screen.getByText(mockInterventionRecommendation.deviation_z.method)).toBeInTheDocument()
    expect(screen.getByText(mockInterventionRecommendation.modeled_impact_reminder)).toBeInTheDocument()
  })
})
