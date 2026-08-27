import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { MerchantProvider } from '@/context/MerchantContext'
import {
  mockControlsList,
  mockEmptyInterventionMemory,
  mockEmptyInterventions,
  mockMerchantList,
  mockMerchantProfile,
  mockSimulationResponse,
} from '@/test/fixtures'

import { SimulatorPage } from './SimulatorPage'

function renderSimulator(initialPath = '/simulator') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <MerchantProvider>
        <SimulatorPage />
      </MerchantProvider>
    </MemoryRouter>,
  )
}

async function moveRefundSlider(value: string) {
  const slider = await screen.findByLabelText('Refund rate (trailing 28 days)')
  fireEvent.change(slider, { target: { value } })
  return slider as HTMLInputElement
}

describe('SimulatorPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
    vi.spyOn(endpoints, 'getMerchantProfile').mockResolvedValue(mockMerchantProfile)
    vi.spyOn(endpoints, 'getSimulationControls').mockResolvedValue(mockControlsList)
    vi.spyOn(endpoints, 'runSimulation').mockResolvedValue(mockSimulationResponse)
    vi.spyOn(endpoints, 'getInterventions').mockResolvedValue(mockEmptyInterventions)
    vi.spyOn(endpoints, 'getInterventionMemory').mockResolvedValue(mockEmptyInterventionMemory)
  })

  it('shows a loading state before merchants have loaded', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {}))
    renderSimulator()
    expect(screen.getByText(/loading merchants/i)).toBeInTheDocument()
  })

  it('renders the intro and three real controls at their observed baseline', async () => {
    renderSimulator()

    expect(await screen.findByText(/what-if simulator/i)).toBeInTheDocument()
    expect(await screen.findByText('Refund rate (trailing 28 days)')).toBeInTheDocument()
    expect(screen.getByText('On-time fulfillment rate (trailing 28 days)')).toBeInTheDocument()
    expect(screen.getByText('New-customer share (trailing 28 days)')).toBeInTheDocument()

    // "Run simulation" is disabled until a control is actually changed.
    expect(screen.getByRole('button', { name: /run simulation/i })).toBeDisabled()
  })

  it('shows an empty state before any simulation has been run', async () => {
    renderSimulator()
    expect(await screen.findByText(/no simulation run yet/i)).toBeInTheDocument()
  })

  it('enables Run simulation once a control is moved, and sends the correct request', async () => {
    renderSimulator()
    await moveRefundSlider('0.5')

    const runButton = screen.getByRole('button', { name: /run simulation/i })
    expect(runButton).toBeEnabled()

    await userEvent.click(runButton)

    await waitFor(() => expect(endpoints.runSimulation).toHaveBeenCalledTimes(1))
    expect(endpoints.runSimulation).toHaveBeenCalledWith(
      'M0001',
      expect.objectContaining({ as_of_date: '2024-06-28', refund_rate_28d: 0.5 }),
    )
    // Only the changed control should be present in the request body.
    const requestBody = vi.mocked(endpoints.runSimulation).mock.calls[0][1]
    expect(requestBody).not.toHaveProperty('fulfillment_on_time_rate_28d')
    expect(requestBody).not.toHaveProperty('new_customer_rate_28d')
  })

  it('displays the modeled impact result returned by the API', async () => {
    renderSimulator()
    await moveRefundSlider('0.5')
    await userEvent.click(screen.getByRole('button', { name: /run simulation/i }))

    expect(await screen.findByText('Modeled impact')).toBeInTheDocument()
    // Values shown come straight from the mocked API response, not invented.
    expect(screen.getAllByText('35.0%').length).toBeGreaterThan(0)
    expect(screen.getByText(mockSimulationResponse.modeled_impact_disclaimer)).toBeInTheDocument()
  })

  it('shows a loading indicator while a simulation is running', async () => {
    vi.spyOn(endpoints, 'runSimulation').mockReturnValue(new Promise(() => {}))
    renderSimulator()
    await moveRefundSlider('0.5')
    await userEvent.click(screen.getByRole('button', { name: /run simulation/i }))

    expect(await screen.findByText(/running simulation on the saved model/i)).toBeInTheDocument()
  })

  it('shows an error state when the simulation request fails', async () => {
    vi.spyOn(endpoints, 'runSimulation').mockRejectedValue(new Error('control value out of range'))
    renderSimulator()
    await moveRefundSlider('0.5')
    await userEvent.click(screen.getByRole('button', { name: /run simulation/i }))

    expect(await screen.findByText('control value out of range')).toBeInTheDocument()
  })

  it('shows an error state when the controls endpoint fails', async () => {
    vi.spyOn(endpoints, 'getSimulationControls').mockRejectedValue(new Error('controls unavailable'))
    renderSimulator()
    expect(await screen.findByText('controls unavailable')).toBeInTheDocument()
  })

  it('reset restores sliders to baseline and clears the result', async () => {
    renderSimulator()
    const slider = await moveRefundSlider('0.5')
    await userEvent.click(screen.getByRole('button', { name: /run simulation/i }))
    expect(await screen.findByText('Modeled impact')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /reset to observed values/i }))

    expect(slider.value).toBe('0.1')
    expect(screen.queryByText('Modeled impact')).not.toBeInTheDocument()
    expect(await screen.findByText(/no simulation run yet/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /run simulation/i })).toBeDisabled()
  })
})
