import { useState } from 'react'

import type { DataQualitySection } from '@/api/types'
import { ProvenanceTag } from '@/components/common/ProvenanceTag'
import { CONFIDENCE_STYLE } from '@/lib/provenance'

export function ConfidenceBadge({ dataQuality }: { dataQuality: DataQualitySection }) {
  const [expanded, setExpanded] = useState(false)
  const style = CONFIDENCE_STYLE[dataQuality.confidence_level]

  return (
    <div className="mt-4 border-t border-border-subtle pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Confidence</span>
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${style.badge}`}>
          {style.label}
        </span>
        <ProvenanceTag provenance={dataQuality.provenance} />
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-muted-foreground underline decoration-dotted hover:text-secondary-foreground"
        >
          {expanded ? 'Hide details' : 'Why this level'}
        </button>
      </div>

      {expanded && (
        <div className="mt-2 rounded-md bg-muted px-3 py-2 text-xs text-secondary-foreground">
          <p className="font-medium text-secondary-foreground">Based on:</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {dataQuality.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          <p className="mt-2 font-medium text-secondary-foreground">Limitations:</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {dataQuality.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
          <p className="mt-2 text-muted-foreground">{dataQuality.basis}</p>
        </div>
      )}
    </div>
  )
}
