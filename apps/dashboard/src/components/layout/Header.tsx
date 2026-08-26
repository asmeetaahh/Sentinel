import { useLocation } from 'react-router-dom'

import { MerchantSelector } from '@/components/common/MerchantSelector'
import { useMerchantContext } from '@/context/MerchantContext'

import { NAV_ITEMS } from './navigation'

export function Header() {
  const { merchants, selectedMerchantId } = useMerchantContext()
  const selected = merchants.find((m) => m.merchant_id === selectedMerchantId)
  const { pathname } = useLocation()
  const pageTitle = NAV_ITEMS.find((item) => item.to === pathname)?.label ?? 'Overview'

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{pageTitle}</h1>
        <p className="text-sm text-slate-500">
          {selected ? (
            <>
              {selected.archetype} · {selected.business_tier} tier
            </>
          ) : (
            'Select a merchant'
          )}
        </p>
      </div>
      <MerchantSelector />
    </header>
  )
}
