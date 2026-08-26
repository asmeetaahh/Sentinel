import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { useMerchants } from '@/hooks/useMerchants'
import type { MerchantListItem } from '@/api/types'

interface MerchantContextValue {
  merchants: MerchantListItem[]
  merchantsLoading: boolean
  merchantsError: unknown
  selectedMerchantId: string | null
  selectMerchant: (merchantId: string) => void
}

const MerchantContext = createContext<MerchantContextValue | null>(null)

export function MerchantProvider({ children }: { children: ReactNode }) {
  const { merchants, loading, error } = useMerchants()
  const [selectedMerchantId, setSelectedMerchantId] = useState<string | null>(null)

  // Default to the first available merchant once the real list has loaded —
  // never a hardcoded merchant id.
  useEffect(() => {
    if (!selectedMerchantId && merchants.length > 0) {
      setSelectedMerchantId(merchants[0].merchant_id)
    }
  }, [merchants, selectedMerchantId])

  const value = useMemo<MerchantContextValue>(
    () => ({
      merchants,
      merchantsLoading: loading,
      merchantsError: error,
      selectedMerchantId,
      selectMerchant: setSelectedMerchantId,
    }),
    [merchants, loading, error, selectedMerchantId],
  )

  return <MerchantContext.Provider value={value}>{children}</MerchantContext.Provider>
}

export function useMerchantContext(): MerchantContextValue {
  const ctx = useContext(MerchantContext)
  if (!ctx) throw new Error('useMerchantContext must be used within a MerchantProvider')
  return ctx
}
