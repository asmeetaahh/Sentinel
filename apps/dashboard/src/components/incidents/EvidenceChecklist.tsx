import type { EvidenceReadiness } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { EVIDENCE_READINESS_STYLE } from '@/lib/provenance'

export function EvidenceChecklist({ evidence }: { evidence: EvidenceReadiness }) {
  const readinessStyle = EVIDENCE_READINESS_STYLE[evidence.readiness_status]
  const requiredItems = evidence.items.filter((item) => item.required)
  const missingLabels = evidence.missing_evidence
    .map((category) => evidence.items.find((item) => item.category === category)?.label ?? category)
    .join(', ')

  return (
    <MetricCard title="Evidence readiness" footer={evidence.disclaimer} emphasized>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${readinessStyle.badge}`}>
          Evidence readiness: {readinessStyle.label.toUpperCase()}
        </span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {evidence.available_count} of {evidence.required_count} required available
        </span>
      </div>

      <ul className="mt-4 divide-y divide-border-subtle">
        {requiredItems.map((item) => (
          <li key={item.category} className="flex items-start gap-3 py-2.5">
            <span
              aria-hidden="true"
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                item.available ? 'bg-emerald-500/20 text-emerald-300' : 'bg-muted text-muted-foreground'
              }`}
            >
              {item.available ? '✓' : '✗'}
            </span>
            <div>
              <p className={`text-sm font-medium ${item.available ? 'text-foreground' : 'text-secondary-foreground'}`}>
                {item.label}
                <span className="sr-only">{item.available ? ' — available' : ' — missing'}</span>
              </p>
              <p className="text-xs text-muted-foreground">{item.available ? item.rationale : `${item.label} is missing. ${item.rationale}`}</p>
            </div>
          </li>
        ))}
      </ul>

      {evidence.missing_evidence.length > 0 && (
        <div className="mt-3 rounded-md bg-muted px-3 py-2">
          <p className="text-xs font-medium text-secondary-foreground">Missing, in priority order:</p>
          <p className="text-xs text-secondary-foreground">{missingLabels}</p>
        </div>
      )}
    </MetricCard>
  )
}
