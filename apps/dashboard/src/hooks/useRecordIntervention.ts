import { useCallback, useState } from 'react'

import { recordIntervention } from '@/api/endpoints'
import type { InterventionMemoryRecord, RecordInterventionRequestBody } from '@/api/types'

interface RecordState {
  data: InterventionMemoryRecord | null
  loading: boolean
  error: unknown
}

const IDLE_STATE: RecordState = { data: null, loading: false, error: null }

/** Imperative, like useSimulation/useAssistant — recording an intervention
 * action is a deliberate, merchant-initiated click, never automatic. */
export function useRecordIntervention(merchantId: string | null) {
  const [state, setState] = useState<RecordState>(IDLE_STATE)

  const record = useCallback(
    async (body: RecordInterventionRequestBody) => {
      if (!merchantId) return
      setState({ data: null, loading: true, error: null })
      try {
        const data = await recordIntervention(merchantId, body)
        setState({ data, loading: false, error: null })
        return data
      } catch (error) {
        setState({ data: null, loading: false, error })
        return undefined
      }
    },
    [merchantId],
  )

  const reset = useCallback(() => setState(IDLE_STATE), [])

  return { ...state, record, reset }
}
