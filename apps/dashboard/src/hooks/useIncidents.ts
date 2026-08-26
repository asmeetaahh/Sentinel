import { listIncidents } from '@/api/endpoints'
import type { IncidentListResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useIncidents(merchantId: string | null): AsyncState<IncidentListResponse> {
  return useAsync(() => {
    if (!merchantId) return Promise.reject(new Error('no merchant selected'))
    return listIncidents(merchantId)
  }, [merchantId])
}
