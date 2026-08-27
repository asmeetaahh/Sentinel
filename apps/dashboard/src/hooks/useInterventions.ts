import { getInterventions } from '@/api/endpoints'
import type { InterventionRecommendationsResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useInterventions(merchantId: string | null, asOfDate?: string | null): AsyncState<InterventionRecommendationsResponse> {
  return useAsync(() => {
    if (!merchantId) return Promise.reject(new Error('no merchant selected'))
    return getInterventions(merchantId, asOfDate ?? undefined)
  }, [merchantId, asOfDate])
}
