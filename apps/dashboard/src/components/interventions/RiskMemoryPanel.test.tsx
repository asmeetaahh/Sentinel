import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { InterventionMemoryRecord } from '@/api/types'
import { mockEmptyInterventionMemory, mockInterventionMemoryRecord, mockInterventionMemoryWithRecords } from '@/test/fixtures'

import { RiskMemoryPanel } from './RiskMemoryPanel'

const simulatedRecord: InterventionMemoryRecord = {
  ...mockInterventionMemoryRecord,
  intervention_id: 'M0001:fulfillment_on_time_rate_28d:2024-06-20',
  control_id: 'fulfillment_on_time_rate_28d',
  recommendation_title: 'Review fulfillment reliability',
  action_status: 'simulated',
  timestamp: '2026-08-20T09:00:00Z',
  simulated_impact: {
    current_probability: 0.42,
    simulated_probability: 0.31,
    probability_delta_absolute: -0.11,
    exposure_current: 1500,
    exposure_simulated: 1100,
    liquidity_stress_current: 0.2,
    liquidity_stress_simulated: 0.15,
    disclaimer: 'Modeled impact, not a guaranteed or causal outcome.',
    provenance: 'modeled',
  },
}

describe('RiskMemoryPanel', () => {
  it('shows an honest empty state with no fabricated history', () => {
    render(<RiskMemoryPanel memory={mockEmptyInterventionMemory} />)
    expect(screen.getByText('No intervention activity recorded yet')).toBeInTheDocument()
    expect(screen.getByText(mockEmptyInterventionMemory.empty_state_note as string)).toBeInTheDocument()
  })

  it('renders a real record with its action status and title from the API', () => {
    render(<RiskMemoryPanel memory={mockInterventionMemoryWithRecords} />)
    expect(screen.getByText('Review refund pressure')).toBeInTheDocument()
    expect(screen.getByText('Acknowledged')).toBeInTheDocument()
  })

  it('every record shows outcome "Not observed", regardless of action status or whether a simulation ran', () => {
    render(
      <RiskMemoryPanel
        memory={{
          merchant_id: 'M0001',
          count: 2,
          records: [mockInterventionMemoryRecord, simulatedRecord],
          empty_state_note: null,
        }}
      />,
    )
    expect(screen.getAllByText('Outcome: Not observed')).toHaveLength(2)
  })

  it('distinguishes a modeled simulated_impact from the observed outcome: shows the modeled probability line but the outcome stays "not observed"', () => {
    render(
      <RiskMemoryPanel
        memory={{
          merchant_id: 'M0001',
          count: 1,
          records: [simulatedRecord],
          empty_state_note: null,
        }}
      />,
    )
    // The modeled simulator result is shown, clearly framed as "modeled probability"...
    expect(screen.getByText(/modeled probability/i)).toBeInTheDocument()
    expect(screen.getByText(/42\.0%/)).toBeInTheDocument()
    expect(screen.getByText(/31\.0%/)).toBeInTheDocument()
    // ...but this never becomes, or is confused with, an observed real-world outcome.
    expect(screen.getByText('Outcome: Not observed')).toBeInTheDocument()
    expect(screen.queryByText('Outcome: Observed')).not.toBeInTheDocument()
  })

  it('a record with no simulation attached (e.g. a plain acknowledgement) shows no fabricated modeled-impact line', () => {
    render(<RiskMemoryPanel memory={mockInterventionMemoryWithRecords} />)
    expect(screen.queryByText(/modeled probability/i)).not.toBeInTheDocument()
  })

  it('renders the outcome_note explaining why the outcome is not observed, verbatim from the API', () => {
    render(<RiskMemoryPanel memory={mockInterventionMemoryWithRecords} />)
    expect(screen.getByText(mockInterventionMemoryRecord.outcome_note)).toBeInTheDocument()
  })

  it('renders newest-first when multiple records exist', () => {
    const older: InterventionMemoryRecord = { ...mockInterventionMemoryRecord, timestamp: '2026-08-01T00:00:00Z' }
    const newer: InterventionMemoryRecord = {
      ...mockInterventionMemoryRecord,
      recommendation_title: 'Review customer-mix shift',
      timestamp: '2026-08-20T00:00:00Z',
    }
    render(
      <RiskMemoryPanel
        memory={{ merchant_id: 'M0001', count: 2, records: [older, newer], empty_state_note: null }}
      />,
    )
    const titles = screen.getAllByText(/Review (refund pressure|customer-mix shift)/)
    expect(titles[0]).toHaveTextContent('Review customer-mix shift')
    expect(titles[1]).toHaveTextContent('Review refund pressure')
  })
})
