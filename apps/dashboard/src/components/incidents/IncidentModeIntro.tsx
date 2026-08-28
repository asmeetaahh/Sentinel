export function IncidentModeIntro({ merchantId }: { merchantId: string }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5 shadow-sm shadow-black/20">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Incident Mode</p>
      <p className="mt-2 max-w-3xl text-sm text-secondary-foreground">
        Each incident below is a synthetic-benchmark risk episode for <span className="font-medium">{merchantId}</span>{' '}
        that the existing saved model actually flagged — the same artifact and decision threshold used by the Risk and
        Simulator screens. Selecting an incident connects that detection through to modeled exposure, liquidity
        stress, verified SHAP drivers, a reason code, and evidence readiness, ending in a preparation workflow that
        always requires merchant confirmation. Sentinel does not fabricate evidence, submit disputes, or claim access
        to Razorpay's actual dispute systems. See docs/architecture/incident_response.md.
      </p>
    </section>
  )
}
