import { MerchantSelector } from '@/components/common/MerchantSelector'
import { useMerchantContext } from '@/context/MerchantContext'

export function Header() {
  const { merchants, selectedMerchantId } = useMerchantContext()
  const selected = merchants.find((m) => m.merchant_id === selectedMerchantId)

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Overview</h1>
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
