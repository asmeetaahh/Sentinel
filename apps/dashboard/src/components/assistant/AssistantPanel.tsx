import { useState, type FormEvent } from 'react'

import type { SimulationRequestBody } from '@/api/types'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { InlineLoadingState, LoadingState } from '@/components/common/LoadingState'
import { MetricCard } from '@/components/common/MetricCard'
import { useAssistant } from '@/hooks/useAssistant'

import { AssistantAnswer } from './AssistantAnswer'
import { SuggestedPrompts } from './SuggestedPrompts'

/**
 * A bounded assistant over already-verified Sentinel context — never the
 * source of the risk score itself. Embedded per-page (Overview, Simulator,
 * Incident Response) rather than as a standalone nav destination, since no
 * existing placeholder for a dedicated AI screen exists in the sidebar; see
 * docs/architecture/ai_orchestrator.md.
 */
export function AssistantPanel({
  merchantId,
  asOfDate,
  incidentId,
  simulation,
  suggestedPrompts,
  title = 'Ask Sentinel',
}: {
  merchantId: string
  asOfDate?: string | null
  incidentId?: string | null
  simulation?: SimulationRequestBody | null
  suggestedPrompts: string[]
  title?: string
}) {
  const assistant = useAssistant(merchantId)
  const [question, setQuestion] = useState('')

  function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return
    setQuestion(trimmed)
    assistant.ask({
      question: trimmed,
      as_of_date: asOfDate ?? undefined,
      incident_id: incidentId ?? undefined,
      simulation: simulation ?? undefined,
    })
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    submit(question)
  }

  return (
    <MetricCard title={title}>
      <p className="mb-3 text-xs text-muted-foreground">
        Ask about this merchant's verified risk, exposure, liquidity, simulation, or incident data. Sentinel's
        assistant explains already-computed results — it does not calculate risk itself.
      </p>

      <SuggestedPrompts prompts={suggestedPrompts} onSelect={submit} disabled={assistant.loading} />

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <label htmlFor="assistant-question" className="sr-only">
          Ask Sentinel a question
        </label>
        <input
          id="assistant-question"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about this merchant's verified context…"
          className="flex-1 rounded-md border border-border px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={assistant.loading || !question.trim()}
          className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {assistant.loading ? <InlineLoadingState /> : 'Ask'}
        </button>
      </form>

      <div className="mt-4">
        {assistant.loading && <LoadingState label="Asking Sentinel's assistant…" />}
        {assistant.error ? <ErrorState error={assistant.error} /> : null}
        {!assistant.loading && !assistant.error && assistant.data && (
          <AssistantAnswer response={assistant.data} onFollowUp={submit} />
        )}
        {!assistant.loading && !assistant.error && !assistant.data && (
          <EmptyState
            title="No question asked yet"
            detail="Try a suggested prompt above, or ask your own question about this merchant's verified context."
          />
        )}
      </div>
    </MetricCard>
  )
}
