import { listMerchants } from '@/api/endpoints'
import type { MerchantListItem } from '@/api/types'

import { useAsync } from './useAsync'

export function useMerchants(): { merchants: MerchantListItem[]; loading: boolean; error: unknown } {
  const { data, loading, error } = useAsync(() => listMerchants(), [])
  return { merchants: data?.merchants ?? [], loading, error }
}
