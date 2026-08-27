import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { mockDataQualityHigh, mockDataQualityLimited, mockDataQualityMedium } from '@/test/fixtures'

import { ConfidenceBadge } from './ConfidenceBadge'

describe('ConfidenceBadge', () => {
  it('renders the correct level label for high confidence', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityHigh} />)
    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('renders the correct level label for medium confidence', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityMedium} />)
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  it('renders the correct level label for limited confidence', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityLimited} />)
    expect(screen.getByText('Limited')).toBeInTheDocument()
  })

  it('shows the Derived provenance tag, never Modeled', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityHigh} />)
    expect(screen.getByText('Derived')).toBeInTheDocument()
    expect(screen.queryByText('Modeled')).not.toBeInTheDocument()
  })

  it('hides the reasons/limitations detail until expanded', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityMedium} />)
    expect(screen.queryByText('Based on:')).not.toBeInTheDocument()
    expect(screen.queryByText('Limitations:')).not.toBeInTheDocument()
  })

  it('expanding "Why this level" reveals the real reasons and limitations text from the API, verbatim', async () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityMedium} />)
    await userEvent.click(screen.getByText('Why this level'))

    expect(screen.getByText('Based on:')).toBeInTheDocument()
    for (const reason of mockDataQualityMedium.reasons) {
      expect(screen.getByText(reason)).toBeInTheDocument()
    }
    expect(screen.getByText('Limitations:')).toBeInTheDocument()
    for (const limitation of mockDataQualityMedium.limitations) {
      expect(screen.getByText(limitation)).toBeInTheDocument()
    }
    expect(screen.getByText(mockDataQualityMedium.basis)).toBeInTheDocument()
  })

  it('toggles back to hidden when clicked again', async () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityHigh} />)
    await userEvent.click(screen.getByText('Why this level'))
    expect(screen.getByText('Hide details')).toBeInTheDocument()

    await userEvent.click(screen.getByText('Hide details'))
    expect(screen.queryByText('Based on:')).not.toBeInTheDocument()
    expect(screen.getByText('Why this level')).toBeInTheDocument()
  })

  it('never renders a numeric or percentage confidence score', () => {
    render(<ConfidenceBadge dataQuality={mockDataQualityHigh} />)
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })
})
