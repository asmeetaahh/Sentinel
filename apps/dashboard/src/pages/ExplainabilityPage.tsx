import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { RiskDrivers } from '@/components/overview/RiskDrivers'
import { useMerchantContext } from '@/context/MerchantContext'
import { useExplanation } from '@/hooks/useExplanation'
import { useMerchantProfile } from '@/hooks/useMerchantProfile'
import { formatDate, formatPercent } from '@/lib/format'

export function ExplainabilityPage() {
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

  return <ExplainabilityContent merchantId={selectedMerchantId} />
}

function ExplainabilityContent({ merchantId }: { merchantId: string }) {
  const profile = useMerchantProfile(merchantId)
  const asOfDate = profile.data?.latest_observed_snapshot.as_of_date ?? null
  const explanation = useExplanation(merchantId, asOfDate, 6)

  if (profile.loading) return <LoadingState label="Loading merchant profile…" />
  if (profile.error) return <ErrorState error={profile.error} />
  if (!profile.data || !asOfDate) return null

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Explainability</p>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          What the model's own SHAP values say about its {formatDate(asOfDate)} prediction for{' '}
          <span className="font-medium">{merchantId}</span> — the same verified drivers shown elsewhere in Sentinel,
          in plain language. SHAP attributes the model's output to its inputs; it does not establish that any feature
          causes elevated risk, and this benchmark was trained entirely on synthetic data.
        </p>
        {explanation.data && (
          <p className="mt-3 text-sm text-slate-600">
            Modeled {explanation.data.horizon_days}-day probability:{' '}
            <span className="font-medium tabular-nums">
              {formatPercent(explanation.data.prediction.model_probability_calibrated)}
            </span>{' '}
            against a decision threshold of{' '}
            <span className="font-medium tabular-nums">{formatPercent(explanation.data.prediction.decision_threshold)}</span>.{' '}
            {explanation.data.prediction.note}
          </p>
        )}
      </section>

      {explanation.loading && <LoadingState label="Computing verified SHAP explanation…" />}
      {explanation.error ? <ErrorState error={explanation.error} /> : null}
      {explanation.data && (
        <>
          <RiskDrivers
            positive={explanation.data.drivers.top_positive_contributors}
            negative={explanation.data.drivers.top_negative_contributors}
            causalityDisclaimer={explanation.data.causality_disclaimer}
          />
          <p className="text-xs leading-relaxed text-slate-400">
            Verified: these SHAP contributions reconstruct the model's own predicted probability to within{' '}
            {explanation.data.faithfulness.reconstruction_error.toExponential(1)} for this prediction — Sentinel
            refuses to display an explanation that fails this reconstruction check, so every driver shown above is
            independently confirmed to match what the model actually computed.
          </p>
        </>
      )}
    </div>
  )
}
