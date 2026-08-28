import { useMerchantContext } from '@/context/MerchantContext'

import { InlineLoadingState } from './LoadingState'

export function MerchantSelector() {
  const { merchants, merchantsLoading, merchantsError, selectedMerchantId, selectMerchant } = useMerchantContext()

  if (merchantsLoading && merchants.length === 0) {
    return <InlineLoadingState />
  }

  if (merchantsError) {
    return <span className="text-xs text-red-400">Merchant list unavailable</span>
  }

  if (merchants.length === 0) {
    return <span className="text-xs text-muted-foreground">No merchants available</span>
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="merchant-selector" className="text-xs font-medium text-muted-foreground">
        Merchant
      </label>
      <select
        id="merchant-selector"
        value={selectedMerchantId ?? ''}
        onChange={(event) => selectMerchant(event.target.value)}
        className="min-w-56 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground shadow-sm focus:border-indigo-400"
      >
        {merchants.map((merchant) => (
          <option key={merchant.merchant_id} value={merchant.merchant_id}>
            {merchant.merchant_id} — {merchant.archetype}
          </option>
        ))}
      </select>
    </div>
  )
}
