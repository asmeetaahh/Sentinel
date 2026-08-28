import { formatDate } from '@/lib/format'

export function SimulatorIntro({ merchantId, asOfDate }: { merchantId: string; asOfDate: string }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5 shadow-sm shadow-black/20">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">What-if simulator</p>
      <p className="mt-2 max-w-3xl text-sm text-secondary-foreground">
        Adjust a small set of bounded, observable operational metrics for <span className="font-medium">{merchantId}</span>{' '}
        (as of {formatDate(asOfDate)}) and see how the same saved research model responds. Every other observed feature
        is held fixed — this is a MODELED IMPACT, a bounded model what-if, not a forecast, guarantee, or causal claim
        about what would actually happen. See docs/architecture/simulator.md for exactly how each control maps to the
        model's inputs.
      </p>
    </section>
  )
}
