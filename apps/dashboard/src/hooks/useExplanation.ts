import { getExplanation } from '@/api/endpoints'
import type { ExplanationResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useExplanation(merchantId: string | null, asOfDate: string | null, topK = 6): AsyncState<ExplanationResponse> {
  return useAsync(() => {
    if (!merchantId || !asOfDate) return Promise.reject(new Error('no merchant/date selected'))
    return getExplanation(merchantId, asOfDate, topK)
  }, [merchantId, asOfDate, topK])
}
