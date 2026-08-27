import type { InterventionMemoryListResponse } from '@/api/types'
import { EmptyState } from '@/components/common/EmptyState'
import { MetricCard } from '@/components/common/MetricCard'
import { formatDateTime, formatPercent } from '@/lib/format'
import { ACTION_STATUS_STYLE, OUTCOME_STATUS_STYLE } from '@/lib/provenance'

export function RiskMemoryPanel({ memory }: { memory: InterventionMemoryListResponse }) {
  return (
    <MetricCard title="Risk Memory (this session)">
      <p className="mb-3 text-xs text-slate-400">
        A lightweight, in-process record of intervention activity for this session only — not a database, and not
        cleared or persisted between backend restarts. This is a prototype decision history, not a validated
        learning system.
      </p>

      {memory.count === 0 ? (
        <EmptyState title="No intervention activity recorded yet" detail={memory.empty_state_note ?? undefined} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {memory.records
            .slice()
            .reverse()
            .map((record, index) => {
              const actionStyle = ACTION_STATUS_STYLE[record.action_status]
              const outcomeStyle = OUTCOME_STATUS_STYLE[record.outcome_status]
              return (
                <li key={`${record.intervention_id}-${record.timestamp}-${index}`} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium text-slate-800">{record.recommendation_title}</span>
                    <span className="text-[11px] text-slate-400 tabular-nums">{formatDateTime(record.timestamp)}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${actionStyle.badge}`}>
                      {actionStyle.label}
                    </span>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${outcomeStyle.badge}`}>
                      Outcome: {outcomeStyle.label}
                    </span>
                  </div>
                  {record.simulated_impact && (
                    <p className="text-xs text-slate-500 tabular-nums">
                      Modeled probability {formatPercent(record.simulated_impact.current_probability)} →{' '}
                      {formatPercent(record.simulated_impact.simulated_probability)}
                    </p>
                  )}
                  <p className="text-[11px] text-slate-400">{record.outcome_note}</p>
                </li>
              )
            })}
        </ul>
      )}
    </MetricCard>
  )
}
