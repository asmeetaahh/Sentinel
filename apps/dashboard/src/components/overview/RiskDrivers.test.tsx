import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RiskDrivers } from './RiskDrivers'
import { mockExplanation } from '@/test/fixtures'

describe('RiskDrivers', () => {
  it('renders real driver feature names, groups, values, and directions from the API response', () => {
    render(
      <RiskDrivers
        positive={mockExplanation.drivers.top_positive_contributors}
        negative={mockExplanation.drivers.top_negative_contributors}
        causalityDisclaimer={mockExplanation.causality_disclaimer}
      />,
    )

    expect(screen.getByText(/Chargeback rate 28d/i)).toBeInTheDocument()
    expect(screen.getByText(/Refund rate 60d/i)).toBeInTheDocument()
    expect(screen.getByText('Contributing to modeled risk')).toBeInTheDocument()
    expect(screen.getByText('Reducing modeled risk')).toBeInTheDocument()
    expect(screen.getByText(mockExplanation.drivers.top_positive_contributors[0].definition)).toBeInTheDocument()
  })

  it('never uses causal language such as "caused"', () => {
    render(
      <RiskDrivers
        positive={mockExplanation.drivers.top_positive_contributors}
        negative={mockExplanation.drivers.top_negative_contributors}
        causalityDisclaimer={mockExplanation.causality_disclaimer}
      />,
    )
    expect(screen.queryByText(/caused/i)).not.toBeInTheDocument()
  })

  it('shows an explicit empty state when there are no drivers, rather than fabricating any', () => {
    render(<RiskDrivers positive={[]} negative={[]} causalityDisclaimer="disclaimer" />)
    expect(screen.getByText(/No driver data available/i)).toBeInTheDocument()
  })
})
