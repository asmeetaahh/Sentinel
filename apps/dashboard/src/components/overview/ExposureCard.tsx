import type { ExposureSection } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { formatAmountCompact } from '@/lib/format'

export function ExposureCard({ exposure }: { exposure: ExposureSection }) {
  return (
    <MetricCard title="Estimated 30-day exposure" provenance={exposure.estimate.provenance} footer={exposure.estimate.note}>
      <p className="text-2xl font-semibold text-slate-800 tabular-nums">{formatAmountCompact(exposure.estimate.value)}</p>
      <p className="mt-1 text-xs text-slate-400">{exposure.estimate.method}</p>

      {exposure.retrospective_actual.available && exposure.retrospective_actual.value !== null && (
        <div className="mt-3 rounded-md bg-slate-50 px-3 py-2">
          <p className="text-[11px] font-medium tracking-wide text-slate-400 uppercase">
            Retrospective outcome (benchmark only)
          </p>
          <p className="text-sm font-medium text-slate-600 tabular-nums">
            {formatAmountCompact(exposure.retrospective_actual.value)}
          </p>
        </div>
      )}
    </MetricCard>
  )
}
