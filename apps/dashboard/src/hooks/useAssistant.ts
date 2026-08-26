import { useCallback, useState } from 'react'

import { askAssistant } from '@/api/endpoints'
import type { AssistantRequestBody, AssistantResponse } from '@/api/types'

interface AssistantState {
  data: AssistantResponse | null
  loading: boolean
  error: unknown
}

const IDLE_STATE: AssistantState = { data: null, loading: false, error: null }

/** Imperative (question-triggered), like useSimulation — asking the
 * assistant is a deliberate user action, not something to auto-run. */
export function useAssistant(merchantId: string | null) {
  const [state, setState] = useState<AssistantState>(IDLE_STATE)

  const ask = useCallback(
    async (body: AssistantRequestBody) => {
      if (!merchantId) return
      setState((prev) => ({ data: prev.data, loading: true, error: null }))
      try {
        const data = await askAssistant(merchantId, body)
        setState({ data, loading: false, error: null })
      } catch (error) {
        setState({ data: null, loading: false, error })
      }
    },
    [merchantId],
  )

  const reset = useCallback(() => setState(IDLE_STATE), [])

  return { ...state, ask, reset }
}
