import { AssistantPanel } from '@/components/assistant/AssistantPanel'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { EmptyState } from '@/components/common/EmptyState'
import { MetricCard } from '@/components/common/MetricCard'
import { InterventionIntelligence } from '@/components/interventions/InterventionIntelligence'
import { RiskMemoryPanel } from '@/components/interventions/RiskMemoryPanel'
import { ExposureCard } from '@/components/overview/ExposureCard'
import { LiquidityCard } from '@/components/overview/LiquidityCard'
import { RiskDrivers } from '@/components/overview/RiskDrivers'
import { RiskSummary } from '@/components/overview/RiskSummary'
import { TrajectoryChart } from '@/components/overview/TrajectoryChart'
import { useMerchantContext } from '@/context/MerchantContext'
import { useExplanation } from '@/hooks/useExplanation'
import { useInterventionMemory } from '@/hooks/useInterventionMemory'
import { useInterventions } from '@/hooks/useInterventions'
import { useMerchantProfile } from '@/hooks/useMerchantProfile'
import { useObservations } from '@/hooks/useObservations'
import { useRisk } from '@/hooks/useRisk'
import { formatDate, formatPercent } from '@/lib/format'

export function OverviewPage() {
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

  return <OverviewContent merchantId={selectedMerchantId} />
}

function OverviewContent({ merchantId }: { merchantId: string }) {
  const profile = useMerchantProfile(merchantId)
  const asOfDate = profile.data?.latest_observed_snapshot.as_of_date ?? null

  const risk = useRisk(merchantId, asOfDate)
  const explanation = useExplanation(merchantId, asOfDate, 6)
  const observations = useObservations(merchantId, 90)
  const interventions = useInterventions(merchantId, asOfDate)
  const memory = useInterventionMemory(merchantId)

  if (profile.loading) return <LoadingState label="Loading merchant profile…" />
  if (profile.error) return <ErrorState error={profile.error} />
  if (!profile.data) return null

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-border bg-card p-5 shadow-sm shadow-black/20">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Current merchant state</p>
            <p className="text-sm text-secondary-foreground">
              {profile.data.merchant_id} · signed up {formatDate(profile.data.signup_date)} ·{' '}
              {profile.data.weekly_seasonality_profile.replace('_', ' ')}
            </p>
          </div>
          <div className="flex gap-6 text-right text-sm">
            <Stat label="Latest GMV" value={profile.data.latest_observed_snapshot.gmv.toFixed(0)} />
            <Stat label="Transactions" value={String(profile.data.latest_observed_snapshot.transaction_count)} />
            <Stat label="On-time fulfillment" value={formatPercent(profile.data.latest_observed_snapshot.fulfillment_on_time_rate)} />
          </div>
        </div>
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

      {explanation.loading && <LoadingState label="Computing verified SHAP explanation…" />}
      {explanation.error ? (
        <div>
          <p className="mb-2 text-sm font-medium text-secondary-foreground">Verified model drivers</p>
          <ErrorState error={explanation.error} />
        </div>
      ) : null}
      {explanation.data && (
        <RiskDrivers
          positive={explanation.data.drivers.top_positive_contributors}
          negative={explanation.data.drivers.top_negative_contributors}
          causalityDisclaimer={explanation.data.causality_disclaimer}
        />
      )}

      {interventions.loading && <LoadingState label="Evaluating intervention candidates…" />}
      {interventions.error ? <ErrorState error={interventions.error} /> : null}
      {interventions.data && (
        <InterventionIntelligence merchantId={merchantId} interventions={interventions.data} onRecorded={memory.refetch} />
      )}

      {memory.loading && <LoadingState label="Loading Risk Memory…" />}
      {memory.error ? <ErrorState error={memory.error} /> : null}
      {memory.data && <RiskMemoryPanel memory={memory.data} />}

      <AssistantPanel
        key={merchantId}
        merchantId={merchantId}
        asOfDate={asOfDate}
        suggestedPrompts={[
          'Why is my risk elevated?',
          'What should I consider reviewing?',
          'What does this mean for liquidity?',
        ]}
      />
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
      <p className="font-semibold text-foreground tabular-nums">{value}</p>
    </div>
  )
}
