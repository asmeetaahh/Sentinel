import { useCallback, useState } from 'react'

import { getInterventionMemory } from '@/api/endpoints'

import { useAsync } from './useAsync'

/** Like the other useAsync-based hooks, but exposes `refetch` — Risk
 * Memory changes as a side effect of an action taken elsewhere (recording
 * an intervention), not from a prop changing, so something has to be able
 * to ask it to reload. */
export function useInterventionMemory(merchantId: string | null) {
  const [refreshKey, setRefreshKey] = useState(0)
  const state = useAsync(() => {
    if (!merchantId) return Promise.reject(new Error('no merchant selected'))
    return getInterventionMemory(merchantId)
  }, [merchantId, refreshKey])

  const refetch = useCallback(() => setRefreshKey((key) => key + 1), [])

  return { ...state, refetch }
}
