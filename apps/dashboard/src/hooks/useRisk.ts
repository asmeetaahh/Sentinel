import { getRisk } from '@/api/endpoints'
import type { RiskResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useRisk(merchantId: string | null, asOfDate: string | null): AsyncState<RiskResponse> {
  return useAsync(() => {
    if (!merchantId || !asOfDate) return Promise.reject(new Error('no merchant/date selected'))
    return getRisk(merchantId, asOfDate)
  }, [merchantId, asOfDate])
}
