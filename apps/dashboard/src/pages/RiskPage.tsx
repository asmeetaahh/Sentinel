import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { MetricCard } from '@/components/common/MetricCard'
import { ExposureCard } from '@/components/overview/ExposureCard'
import { LiquidityCard } from '@/components/overview/LiquidityCard'
import { RiskSummary } from '@/components/overview/RiskSummary'
import { TrajectoryChart } from '@/components/overview/TrajectoryChart'
import { useMerchantContext } from '@/context/MerchantContext'
import { useMerchantProfile } from '@/hooks/useMerchantProfile'
import { useObservations } from '@/hooks/useObservations'
import { useRisk } from '@/hooks/useRisk'
import { formatDate } from '@/lib/format'

export function RiskPage() {
  const { merchantsLoading, merchantsError, selectedMerchantId } = useMerchantContext()

  if (merchantsLoading && !selectedMerchantId) {
    return <LoadingState label="Loading merchants…" />
  }
  if (merchantsError) {
    return <ErrorState error={merchantsError} />
  }
  if (!selectedMerchantId) {
    return <EmptyState title="No merchants available" detail="The benchmark returned no merchants to display." />
  }

  return <RiskContent merchantId={selectedMerchantId} />
}

function RiskContent({ merchantId }: { merchantId: string }) {
  const profile = useMerchantProfile(merchantId)
  const asOfDate = profile.data?.latest_observed_snapshot.as_of_date ?? null

  const risk = useRisk(merchantId, asOfDate)
  const observations = useObservations(merchantId, 90)

  if (profile.loading) return <LoadingState label="Loading merchant profile…" />
  if (profile.error) return <ErrorState error={profile.error} />
  if (!profile.data || !asOfDate) return null

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Risk Engine</p>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          The verified 30-day chargeback-risk assessment for <span className="font-medium">{merchantId}</span> as of{' '}
          {formatDate(asOfDate)} — the same saved model, decision threshold, exposure estimate, liquidity-stress
          calculation, and confidence/data-quality signal used everywhere else in Sentinel. This page presents that
          single verified assessment; it does not compute a second one.
        </p>
      </section>

      {risk.loading && <LoadingState label="Scoring merchant risk…" />}
      {risk.error ? <ErrorState error={risk.error} /> : null}
      {risk.data && <RiskSummary risk={risk.data} />}

      {risk.data && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <ExposureCard exposure={risk.data.exposure} />
          <LiquidityCard liquidity={risk.data.liquidity} />
        </div>
      )}

      <MetricCard title="Recent trajectory (last 90 observed days)">
        {observations.loading && <LoadingState label="Loading historical observations…" />}
        {observations.error ? <ErrorState error={observations.error} /> : null}
        {observations.data && <TrajectoryChart observations={observations.data.observations} />}
      </MetricCard>
    </div>
  )
}
