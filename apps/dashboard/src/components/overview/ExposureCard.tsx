import type { ExposureSection } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { formatAmountCompact } from '@/lib/format'

export function ExposureCard({ exposure }: { exposure: ExposureSection }) {
  return (
    <MetricCard title="Estimated 30-day exposure" provenance={exposure.estimate.provenance} footer={exposure.estimate.note}>
      <p className="text-2xl font-semibold text-foreground tabular-nums">{formatAmountCompact(exposure.estimate.value)}</p>
      <p className="mt-1 text-xs text-muted-foreground">{exposure.estimate.method}</p>

      {exposure.retrospective_actual.available && exposure.retrospective_actual.value !== null && (
        <div className="mt-3 rounded-md bg-muted px-3 py-2">
          <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            Retrospective outcome (benchmark only)
          </p>
          <p className="text-sm font-medium text-secondary-foreground tabular-nums">
            {formatAmountCompact(exposure.retrospective_actual.value)}
          </p>
        </div>
      )}
    </MetricCard>
  )
}
