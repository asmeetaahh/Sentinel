import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { MerchantProvider } from '@/context/MerchantContext'
import { mockIncidentDetail, mockIncidentList, mockMerchantList } from '@/test/fixtures'

import { EvidencePage } from './EvidencePage'

function renderEvidencePage() {
  return render(
    <MerchantProvider>
      <EvidencePage />
    </MerchantProvider>,
  )
}

describe('EvidencePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'listIncidents').mockResolvedValue(mockIncidentList)
    vi.spyOn(endpoints, 'getIncident').mockResolvedValue(mockIncidentDetail)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {}))
    renderEvidencePage()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('renders the incident list and auto-selects the first incident', async () => {
    renderEvidencePage()
    expect(await screen.findByText('INC-E0001000')).toBeInTheDocument()
    expect(screen.getByText('INC-E0001001')).toBeInTheDocument()
    await waitFor(() => expect(endpoints.getIncident).toHaveBeenCalledWith('INC-E0001000'))
  })

  it('renders real evidence readiness status distinguishing available from missing', async () => {
    renderEvidencePage()
    expect(await screen.findByText(/Evidence readiness: PARTIAL/i)).toBeInTheDocument()
    expect(screen.getByText('Invoice')).toBeInTheDocument()
    expect(screen.getByText('Delivery proof')).toBeInTheDocument()
    expect(screen.getByText(/Missing, in priority order/i)).toBeInTheDocument()
  })

  it('renders the real estimated case count', async () => {
    renderEvidencePage()
    expect(await screen.findByText('Affected cases (estimated)')).toBeInTheDocument()
    expect(screen.getByText(String(mockIncidentDetail.case_summary.estimated_case_count))).toBeInTheDocument()
  })

  it('switches the evidence detail pane when a different incident is selected', async () => {
    vi.spyOn(endpoints, 'getIncident').mockImplementation((id: string) =>
      Promise.resolve({ ...mockIncidentDetail, incident_id: id }),
    )
    renderEvidencePage()
    await screen.findByText('INC-E0001000')
    await userEvent.click(screen.getByText('INC-E0001001'))
    await waitFor(() => expect(endpoints.getIncident).toHaveBeenCalledWith('INC-E0001001'))
  })

  it('shows an honest empty state for a merchant with no incidents', async () => {
    vi.spyOn(endpoints, 'listIncidents').mockResolvedValue({ merchant_id: 'M0001', count: 0, incidents: [] })
    renderEvidencePage()
    expect(await screen.findByText(/no incidents detected for this merchant/i)).toBeInTheDocument()
  })

  it('shows an error state when the incident list fails to load', async () => {
    vi.spyOn(endpoints, 'listIncidents').mockRejectedValue(new Error('incidents unavailable'))
    renderEvidencePage()
    expect(await screen.findByText('incidents unavailable')).toBeInTheDocument()
  })

  it('shows an error state when a single incident fails to load', async () => {
    vi.spyOn(endpoints, 'getIncident').mockRejectedValue(new Error('incident detail unavailable'))
    renderEvidencePage()
    expect(await screen.findByText('incident detail unavailable')).toBeInTheDocument()
  })

  it('never renders a fabricated document, tracking number, or message body', async () => {
    renderEvidencePage()
    await screen.findByText(/Evidence readiness: PARTIAL/i)
    const bodyText = document.body.textContent ?? ''
    expect(bodyText).not.toMatch(/TRK\d+/)
    expect(bodyText).not.toMatch(/INV-\d+/)
    expect(bodyText.toLowerCase()).not.toContain('dear customer')
  })

  it('does not render the full response-preparation workflow — that stays on Incident Response', async () => {
    renderEvidencePage()
    await screen.findByText(/Evidence readiness: PARTIAL/i)
    expect(screen.queryByRole('button', { name: /prepare response/i })).not.toBeInTheDocument()
  })
})
