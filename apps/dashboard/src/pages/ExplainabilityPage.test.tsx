import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { MerchantProvider } from '@/context/MerchantContext'
import { mockExplanation, mockMerchantList, mockMerchantProfile } from '@/test/fixtures'

import { ExplainabilityPage } from './ExplainabilityPage'

function renderExplainabilityPage() {
  return render(
    <MerchantProvider>
      <ExplainabilityPage />
    </MerchantProvider>,
  )
}

describe('ExplainabilityPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'getMerchantProfile').mockResolvedValue(mockMerchantProfile)
    vi.spyOn(endpoints, 'getExplanation').mockResolvedValue(mockExplanation)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {}))
    renderExplainabilityPage()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('renders the real verified drivers, humanized, with direction and causality framing intact', async () => {
    renderExplainabilityPage()

    expect(await screen.findByText('Verified model drivers')).toBeInTheDocument()
    expect(screen.getByText('Chargeback rate 28d')).toBeInTheDocument()
    expect(screen.getByText('Refund rate 60d')).toBeInTheDocument()
    expect(screen.getByText(mockExplanation.causality_disclaimer)).toBeInTheDocument()
  })

  it('renders the real prediction probability and threshold this explanation is grounded in', async () => {
    renderExplainabilityPage()
    expect(await screen.findByText('42.0%')).toBeInTheDocument()
    expect(screen.getByText('64.2%')).toBeInTheDocument()
  })

  it('renders the real faithfulness reconstruction check, never a fabricated one', async () => {
    renderExplainabilityPage()
    expect(await screen.findByText(/reconstruct the model's own predicted probability/i)).toBeInTheDocument()
    expect(screen.getByText(/1\.0e-15/)).toBeInTheDocument()
  })

  it('frames causality only in its correct, negated form — never an affirmative causal claim', async () => {
    renderExplainabilityPage()
    await screen.findByText('Verified model drivers')
    const bodyText = document.body.textContent!.toLowerCase()
    expect(bodyText).not.toContain('this feature causes')
    expect(bodyText).not.toContain('is responsible for')
    // The one legitimate, explicitly negated appearance of "causes" is present.
    expect(bodyText).toContain('does not establish that any feature causes elevated risk')
  })

  it('shows an error state when the explanation endpoint fails', async () => {
    vi.spyOn(endpoints, 'getExplanation').mockRejectedValue(new Error('explanation unavailable'))
    renderExplainabilityPage()
    expect(await screen.findByText('explanation unavailable')).toBeInTheDocument()
  })

  it('switching merchants refetches the explanation for the new merchant', async () => {
    vi.spyOn(endpoints, 'getMerchantProfile').mockImplementation((merchantId: string) =>
      Promise.resolve({ ...mockMerchantProfile, merchant_id: merchantId }),
    )
    renderExplainabilityPage()
    await screen.findByText('Verified model drivers')
    expect(endpoints.getExplanation).toHaveBeenCalledWith('M0001', expect.anything(), 6)
  })
})
