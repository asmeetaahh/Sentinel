import { getMerchantProfile } from '@/api/endpoints'
import type { MerchantProfileResponse } from '@/api/types'

import { useAsync, type AsyncState } from './useAsync'

export function useMerchantProfile(merchantId: string | null): AsyncState<MerchantProfileResponse> {
  return useAsync(() => {
    if (!merchantId) return Promise.reject(new Error('no merchant selected'))
    return getMerchantProfile(merchantId)
  }, [merchantId])
}
