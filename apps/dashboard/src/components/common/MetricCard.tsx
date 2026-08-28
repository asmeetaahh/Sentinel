import type { ReactNode } from 'react'
import type { Provenance } from '@/api/types'

import { ProvenanceTag } from './ProvenanceTag'

interface MetricCardProps {
  title: string
  provenance?: Provenance
  children: ReactNode
  footer?: ReactNode
  /** Reserved for the small number of genuinely primary cards on a screen
   * (e.g. a just-run simulation result) — adds a restrained purple edge
   * glow. Deliberately opt-in and rare: most cards stay neutral so the
   * emphasis stays meaningful. */
  emphasized?: boolean
}

export function MetricCard({ title, provenance, children, footer, emphasized }: MetricCardProps) {
  return (
    <section
      className={`flex flex-col gap-3 rounded-xl border p-5 shadow-sm transition-shadow ${
        emphasized
          ? 'border-indigo-500/25 bg-card shadow-[0_0_28px_-14px_rgba(129,140,248,0.45)]'
          : 'border-border bg-card shadow-black/20'
      }`}
    >
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-secondary-foreground">{title}</h3>
        {provenance && <ProvenanceTag provenance={provenance} />}
      </header>
      <div className="flex-1">{children}</div>
      {footer && <footer className="border-t border-border-subtle pt-3 text-xs text-muted-foreground">{footer}</footer>}
    </section>
  )
}
