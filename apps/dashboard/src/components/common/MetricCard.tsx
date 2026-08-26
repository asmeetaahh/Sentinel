import type { ReactNode } from 'react'
import type { Provenance } from '@/api/types'

import { ProvenanceTag } from './ProvenanceTag'

interface MetricCardProps {
  title: string
  provenance?: Provenance
  children: ReactNode
  footer?: ReactNode
}

export function MetricCard({ title, provenance, children, footer }: MetricCardProps) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-500">{title}</h3>
        {provenance && <ProvenanceTag provenance={provenance} />}
      </header>
      <div className="flex-1">{children}</div>
      {footer && <footer className="border-t border-slate-100 pt-3 text-xs text-slate-400">{footer}</footer>}
    </section>
  )
}
