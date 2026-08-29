import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

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

// Remembers the last-selected merchant across browser refreshes. Never a
// hardcoded merchant id — only ever a value the user themselves picked, and
// only ever trusted once it's been checked against a freshly fetched real
// merchant list (see the restore effect below).
const SELECTED_MERCHANT_STORAGE_KEY = 'sentinel:selectedMerchantId'

function readStoredMerchantId(): string | null {
  try {
    return window.localStorage.getItem(SELECTED_MERCHANT_STORAGE_KEY)
  } catch {
    // Storage unavailable (private browsing, disabled storage, non-browser
    // test environment, etc.) — restoring is a convenience, never required.
    return null
  }
}

function writeStoredMerchantId(merchantId: string): void {
  try {
    window.localStorage.setItem(SELECTED_MERCHANT_STORAGE_KEY, merchantId)
  } catch {
    // Same as above — persistence is best-effort only.
  }
}

export function MerchantProvider({ children }: { children: ReactNode }) {
  const { merchants, loading, error } = useMerchants()
  const [selectedMerchantId, setSelectedMerchantId] = useState<string | null>(null)

  // Once the real merchant list has loaded: restore the previously-selected
  // merchant only if it still exists in that list, otherwise fall back to
  // the first returned merchant — never a hardcoded id either way.
  useEffect(() => {
    if (!selectedMerchantId && merchants.length > 0) {
      const storedMerchantId = readStoredMerchantId()
      const restoredMerchantId =
        storedMerchantId && merchants.some((merchant) => merchant.merchant_id === storedMerchantId) ? storedMerchantId : null
      setSelectedMerchantId(restoredMerchantId ?? merchants[0].merchant_id)
    }
  }, [merchants, selectedMerchantId])

  const selectMerchant = useCallback((merchantId: string) => {
    setSelectedMerchantId(merchantId)
    writeStoredMerchantId(merchantId)
  }, [])

  const value = useMemo<MerchantContextValue>(
    () => ({
      merchants,
      merchantsLoading: loading,
      merchantsError: error,
      selectedMerchantId,
      selectMerchant,
    }),
    [merchants, loading, error, selectedMerchantId, selectMerchant],
  )

  return <MerchantContext.Provider value={value}>{children}</MerchantContext.Provider>
}

export function useMerchantContext(): MerchantContextValue {
  const ctx = useContext(MerchantContext)
  if (!ctx) throw new Error('useMerchantContext must be used within a MerchantProvider')
  return ctx
}
