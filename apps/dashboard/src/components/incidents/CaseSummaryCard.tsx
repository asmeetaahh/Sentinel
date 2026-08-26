import type { CaseSummary } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'

export function CaseSummaryCard({ caseSummary }: { caseSummary: CaseSummary }) {
  return (
    <MetricCard title="Affected cases (estimated)" provenance={caseSummary.provenance} footer={caseSummary.note}>
      <p className="text-2xl font-semibold text-slate-800 tabular-nums">{caseSummary.estimated_case_count}</p>
      <p className="mt-1 text-xs text-slate-400">{caseSummary.method}</p>
    </MetricCard>
  )
}
