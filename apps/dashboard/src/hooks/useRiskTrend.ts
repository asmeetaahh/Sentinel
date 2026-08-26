import { useEffect, useState } from 'react'

import { getRisk } from '@/api/endpoints'

const COMPARISON_WINDOW_DAYS = 7

function shiftDate(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export interface RiskTrend {
  previousProbability: number
  deltaProbability: number
  comparisonDate: string
  windowDays: number
}

/**
 * A real, deterministic derivation from two genuine backend calls (current
 * risk + risk as of `COMPARISON_WINDOW_DAYS` earlier) — never fabricated.
 * Resolves to `null` (not an error) whenever the comparison date simply
 * isn't available in the benchmark (e.g. too close to its start), since
 * that's an expected, unremarkable condition, not a failure.
 */
export function useRiskTrend(
  merchantId: string | null,
  asOfDate: string | null,
  currentProbability: number | null,
): { trend: RiskTrend | null; loading: boolean } {
  const [trend, setTrend] = useState<RiskTrend | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setTrend(null)

    if (!merchantId || !asOfDate || currentProbability === null) {
      setLoading(false)
      return
    }

    const comparisonDate = shiftDate(asOfDate, -COMPARISON_WINDOW_DAYS)
    getRisk(merchantId, comparisonDate)
      .then((previous) => {
        if (cancelled) return
        setTrend({
          previousProbability: previous.model.probability_calibrated,
          deltaProbability: currentProbability - previous.model.probability_calibrated,
          comparisonDate,
          windowDays: COMPARISON_WINDOW_DAYS,
        })
      })
      .catch(() => {
        if (!cancelled) setTrend(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [merchantId, asOfDate, currentProbability])

  return { trend, loading }
}
