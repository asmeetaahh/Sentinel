import { getSimulationControls } from '@/api/endpoints'
import type { ControlsListResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useSimulationControls(merchantId: string | null, asOfDate: string | null): AsyncState<ControlsListResponse> {
  return useAsync(() => {
    if (!merchantId || !asOfDate) return Promise.reject(new Error('no merchant/date selected'))
    return getSimulationControls(merchantId, asOfDate)
  }, [merchantId, asOfDate])
}
