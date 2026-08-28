import type { IncidentSummary } from '@/api/types'
import { formatShortDate } from '@/lib/format'
import { EVIDENCE_READINESS_STYLE, PRIORITY_STYLE } from '@/lib/provenance'

export function IncidentList({
  incidents,
  selectedIncidentId,
  onSelect,
}: {
  incidents: IncidentSummary[]
  selectedIncidentId: string | null
  onSelect: (incidentId: string) => void
}) {
  return (
    <nav aria-label="Incidents" className="flex flex-wrap gap-2">
      {incidents.map((incident) => {
        const isSelected = incident.incident_id === selectedIncidentId
        const priorityStyle = PRIORITY_STYLE[incident.priority]
        const readinessStyle = EVIDENCE_READINESS_STYLE[incident.evidence_readiness_status]

        return (
          <button
            key={incident.incident_id}
            type="button"
            onClick={() => onSelect(incident.incident_id)}
            aria-current={isSelected ? 'true' : undefined}
            title={incident.reason_code_label}
            className={`flex max-w-full items-center gap-2 rounded-lg border px-3 py-2 text-left transition-all duration-150 ${
              isSelected
                ? 'border-indigo-500/40 bg-indigo-500/10 shadow-[0_0_16px_-6px_rgba(129,140,248,0.4)]'
                : 'border-border bg-card hover:border-indigo-500/15 hover:bg-muted'
            }`}
          >
            <span className="text-xs font-semibold text-foreground">{incident.incident_id}</span>
            <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${priorityStyle.badge}`}>{priorityStyle.label}</span>
            <span className="hidden max-w-40 truncate text-[11px] text-secondary-foreground md:inline">
              {incident.reason_code_label}
            </span>
            <span className="hidden text-[10px] text-muted-foreground lg:inline">
              {formatShortDate(incident.window.start_date)}–{formatShortDate(incident.window.end_date)}
            </span>
            <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${readinessStyle.badge}`}>{readinessStyle.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
