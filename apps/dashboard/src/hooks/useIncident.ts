import { getIncident } from '@/api/endpoints'
import type { IncidentDetail } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useIncident(incidentId: string | null): AsyncState<IncidentDetail> {
  return useAsync(() => {
    if (!incidentId) return Promise.reject(new Error('no incident selected'))
    return getIncident(incidentId)
  }, [incidentId])
}
