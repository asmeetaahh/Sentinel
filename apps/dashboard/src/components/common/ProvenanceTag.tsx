import type { Provenance } from '@/api/types'
import { PROVENANCE_LABEL, PROVENANCE_STYLE } from '@/lib/provenance'

export function ProvenanceTag({ provenance }: { provenance: Provenance }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase ${PROVENANCE_STYLE[provenance]}`}
    >
      {PROVENANCE_LABEL[provenance]}
    </span>
  )
}
