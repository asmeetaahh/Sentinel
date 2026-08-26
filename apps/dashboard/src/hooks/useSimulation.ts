import { useCallback, useState } from 'react'

import { runSimulation } from '@/api/endpoints'
import type { SimulationRequestBody, SimulationResponse } from '@/api/types'

interface SimulationState {
  data: SimulationResponse | null
  loading: boolean
  error: unknown
}

const IDLE_STATE: SimulationState = { data: null, loading: false, error: null }

/** Imperative (button-triggered), unlike the other useAsync-based hooks —
 * a simulation is a deliberate user action, not something to auto-run
 * whenever inputs change. */
export function useSimulation(merchantId: string | null) {
  const [state, setState] = useState<SimulationState>(IDLE_STATE)

  const run = useCallback(
    async (body: SimulationRequestBody) => {
      if (!merchantId) return
      setState((prev) => ({ data: prev.data, loading: true, error: null }))
      try {
        const data = await runSimulation(merchantId, body)
        setState({ data, loading: false, error: null })
      } catch (error) {
        setState({ data: null, loading: false, error })
      }
    },
    [merchantId],
  )

  const reset = useCallback(() => setState(IDLE_STATE), [])

  return { ...state, run, reset }
}
