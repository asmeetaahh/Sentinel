import { getObservations } from '@/api/endpoints'
import type { ObservationsResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useObservations(merchantId: string | null, limit = 90): AsyncState<ObservationsResponse> {
  return useAsync(() => {
    if (!merchantId) return Promise.reject(new Error('no merchant selected'))
    return getObservations(merchantId, { limit })
  }, [merchantId, limit])
}
