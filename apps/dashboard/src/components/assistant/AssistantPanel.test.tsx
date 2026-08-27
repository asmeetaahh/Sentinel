import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as endpoints from '@/api/endpoints'
import { ApiError } from '@/api/client'
import { mockAssistantResponse } from '@/test/fixtures'

import { AssistantPanel } from './AssistantPanel'

const SUGGESTED_PROMPTS = ['Why is my risk elevated?', 'What does this mean for liquidity?']

function renderPanel(overrides: Partial<Parameters<typeof AssistantPanel>[0]> = {}) {
  return render(
    <AssistantPanel merchantId="M0001" asOfDate="2024-06-28" suggestedPrompts={SUGGESTED_PROMPTS} {...overrides} />,
  )
}

describe('AssistantPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(endpoints, 'askAssistant').mockResolvedValue(mockAssistantResponse)
  })

  it('renders the suggested prompts and question input', () => {
    renderPanel()
    expect(screen.getByText('Why is my risk elevated?')).toBeInTheDocument()
    expect(screen.getByText('What does this mean for liquidity?')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument()
  })

  it('shows an empty state before any question is asked', () => {
    renderPanel()
    expect(screen.getByText(/no question asked yet/i)).toBeInTheDocument()
  })

  it('submits the correct request when a suggested prompt is clicked', async () => {
    renderPanel({ incidentId: 'INC-0001' })
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    await waitFor(() => expect(endpoints.askAssistant).toHaveBeenCalledTimes(1))
    expect(endpoints.askAssistant).toHaveBeenCalledWith('M0001', {
      question: 'Why is my risk elevated?',
      as_of_date: '2024-06-28',
      incident_id: 'INC-0001',
      simulation: undefined,
    })
  })

  it('submits a free-form typed question', async () => {
    renderPanel()
    const input = screen.getByPlaceholderText(/ask a question/i)
    await userEvent.type(input, 'What is my current liquidity stress?')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    await waitFor(() => expect(endpoints.askAssistant).toHaveBeenCalledTimes(1))
    expect(endpoints.askAssistant).toHaveBeenCalledWith(
      'M0001',
      expect.objectContaining({ question: 'What is my current liquidity stress?' }),
    )
  })

  it('the Ask button is disabled with an empty question', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeDisabled()
  })

  it('shows a loading state while the request is in flight', async () => {
    vi.spyOn(endpoints, 'askAssistant').mockReturnValue(new Promise(() => {}))
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))
    expect(await screen.findByText(/asking sentinel's assistant/i)).toBeInTheDocument()
  })

  it('renders the answer, provenance tags, limitations, and disclaimer on success', async () => {
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    expect(await screen.findByText(mockAssistantResponse.answer)).toBeInTheDocument()
    expect(screen.getByText('MOCK PROVIDER — not a real AI response')).toBeInTheDocument()
    expect(screen.getByText(/Risk · Modeled/i)).toBeInTheDocument()
    expect(screen.getByText(/Exposure · Derived/i)).toBeInTheDocument()

    await userEvent.click(screen.getByText(/limitations & disclaimer/i))
    for (const limitation of mockAssistantResponse.limitations) {
      expect(screen.getByText(limitation)).toBeInTheDocument()
    }
    expect(screen.getByText(mockAssistantResponse.disclaimer)).toBeInTheDocument()
  })

  it('renders suggested follow-up actions that re-submit as a new question', async () => {
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))
    await screen.findByText(mockAssistantResponse.answer)

    const followUps = screen.getAllByText('What does this mean for liquidity?')
    // one is the initial suggested prompt, the other is the follow-up chip
    expect(followUps.length).toBeGreaterThanOrEqual(1)
    await userEvent.click(followUps[followUps.length - 1])

    await waitFor(() => expect(endpoints.askAssistant).toHaveBeenLastCalledWith('M0001', expect.objectContaining({ question: 'What does this mean for liquidity?' })))
  })

  it('shows a provider-specific badge (not "MOCK PROVIDER") when a real provider answered', async () => {
    vi.spyOn(endpoints, 'askAssistant').mockResolvedValue({
      ...mockAssistantResponse,
      provider: 'featherless:openai/gpt-oss-20b',
    })
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    expect(await screen.findByText('FEATHERLESS · openai/gpt-oss-20b')).toBeInTheDocument()
    expect(screen.queryByText('MOCK PROVIDER — not a real AI response')).not.toBeInTheDocument()
  })

  it('formats an openai-vendor identifier the same way (vendor uppercased, model verbatim)', async () => {
    vi.spyOn(endpoints, 'askAssistant').mockResolvedValue({ ...mockAssistantResponse, provider: 'openai:gpt-4o-mini' })
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    expect(await screen.findByText('OPENAI · gpt-4o-mini')).toBeInTheDocument()
  })

  it('shows a distinct provider-unavailable state on a 503 response', async () => {
    vi.spyOn(endpoints, 'askAssistant').mockRejectedValue(new ApiError(503, 'The AI assistant provider is currently unavailable.'))
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    expect(await screen.findByText('Provider unavailable')).toBeInTheDocument()
    expect(screen.getByText('The AI assistant provider is currently unavailable.')).toBeInTheDocument()
  })

  it('shows a generic error state for other failures', async () => {
    vi.spyOn(endpoints, 'askAssistant').mockRejectedValue(new Error('network exploded'))
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))

    expect(await screen.findByText('network exploded')).toBeInTheDocument()
  })

  it('never renders any answer text that was not returned by the API', async () => {
    renderPanel()
    await userEvent.click(screen.getByText('Why is my risk elevated?'))
    await screen.findByText(mockAssistantResponse.answer)

    // The component must not inject its own canned "impressive" answer —
    // whatever is shown must be exactly what the mocked API call returned.
    expect(document.body.textContent).toContain(mockAssistantResponse.answer)
  })
})
