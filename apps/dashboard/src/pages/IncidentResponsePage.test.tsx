import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { MerchantProvider } from '@/context/MerchantContext'
import { mockIncidentDetail, mockIncidentList, mockMerchantList } from '@/test/fixtures'

import { IncidentResponsePage } from './IncidentResponsePage'

function renderIncidentPage() {
  return render(
    <MerchantProvider>
      <IncidentResponsePage />
    </MerchantProvider>,
  )
}

describe('IncidentResponsePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'listIncidents').mockResolvedValue(mockIncidentList)
    vi.spyOn(endpoints, 'getIncident').mockResolvedValue(mockIncidentDetail)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {}))
    renderIncidentPage()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('shows a loading state while incidents are loading', () => {
    vi.spyOn(endpoints, 'listIncidents').mockReturnValue(new Promise(() => {}))
    renderIncidentPage()
    return waitFor(() => expect(screen.getByText(/loading incidents/i)).toBeInTheDocument())
  })

  it('renders the incident list and auto-selects the first incident', async () => {
    renderIncidentPage()

    expect(await screen.findByText('INC-E0001000')).toBeInTheDocument()
    expect(screen.getByText('INC-E0001001')).toBeInTheDocument()

    // The first incident's detail is auto-loaded.
    await waitFor(() => expect(endpoints.getIncident).toHaveBeenCalledWith('INC-E0001000'))
  })

  it('switches the detail pane when a different incident is selected', async () => {
    vi.spyOn(endpoints, 'getIncident').mockImplementation((id: string) =>
      Promise.resolve({ ...mockIncidentDetail, incident_id: id }),
    )
    renderIncidentPage()

    await screen.findByText('INC-E0001000')
    await userEvent.click(screen.getByText('INC-E0001001'))

    await waitFor(() => expect(endpoints.getIncident).toHaveBeenCalledWith('INC-E0001001'))
  })

  it('renders risk context, exposure/liquidity, and verified drivers for the selected incident', async () => {
    renderIncidentPage()

    // Reused Overview components — this is the same real component tree,
    // not a re-implementation, so the same labels appear.
    expect(await screen.findByText('Risk state')).toBeInTheDocument()
    expect(await screen.findByText('Estimated 30-day exposure')).toBeInTheDocument()
    expect(screen.getByText('Available liquidity')).toBeInTheDocument()
    expect(await screen.findByText('Verified model drivers')).toBeInTheDocument()
  })

  it('renders the reason code and its synthetic-prototype disclaimer', async () => {
    renderIncidentPage()
    // Waiting on the disclaimer (detail-pane-only) rather than the reason
    // code label, which also appears on the list card and could resolve
    // before the detail pane has finished loading.
    expect(await screen.findByText(/SENTINEL SYNTHETIC PROTOTYPE TAXONOMY/i)).toBeInTheDocument()
    expect(screen.getAllByText('Goods or service not received').length).toBeGreaterThan(0)
  })

  it('renders evidence readiness status and both available and missing items', async () => {
    renderIncidentPage()

    expect(await screen.findByText(/Evidence readiness: PARTIAL/i)).toBeInTheDocument()
    expect(screen.getByText('Invoice')).toBeInTheDocument()
    expect(screen.getByText('Delivery proof')).toBeInTheDocument()
    expect(screen.getByText('Tracking information')).toBeInTheDocument()
    // Missing evidence is called out explicitly, not hidden.
    expect(screen.getByText(/Missing, in priority order/i)).toBeInTheDocument()
  })

  it('renders priority and the human-readable reasons behind it', async () => {
    renderIncidentPage()
    // Waiting on the reason text (only rendered once the incident DETAIL,
    // not just the list, has loaded) before checking "High priority" —
    // that badge appears on both the list card and the detail header, so
    // checking it first could resolve from the list alone.
    expect(await screen.findByText(/Required evidence for this incident's reason code is incomplete/)).toBeInTheDocument()
    expect(screen.getAllByText('High priority').length).toBeGreaterThan(0)
  })

  it('shows an error state when the incident list fails to load', async () => {
    vi.spyOn(endpoints, 'listIncidents').mockRejectedValue(new Error('incidents unavailable'))
    renderIncidentPage()
    expect(await screen.findByText('incidents unavailable')).toBeInTheDocument()
  })

  it('shows an error state when a single incident fails to load', async () => {
    vi.spyOn(endpoints, 'getIncident').mockRejectedValue(new Error('incident detail unavailable'))
    renderIncidentPage()
    expect(await screen.findByText('incident detail unavailable')).toBeInTheDocument()
  })

  it('shows an empty state for a merchant with no incidents', async () => {
    vi.spyOn(endpoints, 'listIncidents').mockResolvedValue({ merchant_id: 'M0001', count: 0, incidents: [] })
    renderIncidentPage()
    expect(await screen.findByText(/no incidents detected for this merchant/i)).toBeInTheDocument()
  })

  it('the response-preparation workflow requires explicit merchant confirmation and never claims submission', async () => {
    const readyIncident = {
      ...mockIncidentDetail,
      incident_id: 'INC-E0001001',
      evidence_readiness: { ...mockIncidentDetail.evidence_readiness, readiness_status: 'ready' as const },
    }
    vi.spyOn(endpoints, 'getIncident').mockImplementation((id: string) =>
      Promise.resolve(id === 'INC-E0001001' ? readyIncident : mockIncidentDetail),
    )

    renderIncidentPage()
    await screen.findByText('INC-E0001000')

    // Evidence is only PARTIAL for the first incident, so preparation should be blocked.
    expect(await screen.findByText(/Evidence readiness must reach READY/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /prepare response/i })).not.toBeInTheDocument()

    // Switch to the second incident, whose evidence is READY.
    await userEvent.click(screen.getByText('INC-E0001001'))
    const prepareButton = await screen.findByRole('button', { name: /prepare response/i })
    await userEvent.click(prepareButton)

    // Matches the confirmation paragraph specifically (with its trailing
    // period) — the step-tracker label above also reads "Merchant
    // confirmation required" (no period), so a looser match is ambiguous.
    expect(await screen.findByText('Merchant confirmation required.')).toBeInTheDocument()
    expect(screen.getByText(/nothing has been submitted anywhere/i)).toBeInTheDocument()
    expect(screen.getByText(/does not have access/i)).toBeInTheDocument()
  })

  it('never renders a fabricated document, tracking number, or message body', async () => {
    renderIncidentPage()
    await screen.findByText(/Evidence readiness: PARTIAL/i)
    const bodyText = document.body.textContent ?? ''
    expect(bodyText).not.toMatch(/TRK\d+/)
    expect(bodyText).not.toMatch(/INV-\d+/)
    expect(bodyText.toLowerCase()).not.toContain('dear customer')
  })
})
