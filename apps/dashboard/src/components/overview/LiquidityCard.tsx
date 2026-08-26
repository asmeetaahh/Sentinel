import type { LiquiditySection } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { formatAmountCompact, formatRatio } from '@/lib/format'

/** Visual anchor only: 100% bar width = exposure estimate equal to available
 * liquidity (ratio of 1.0) — a mathematically self-evident reference point,
 * not an invented severity threshold. Capped visually at 150%. */
const GAUGE_MAX_RATIO = 1.5

export function LiquidityCard({ liquidity }: { liquidity: LiquiditySection }) {
  const stressValue = liquidity.liquidity_stress.value
  const barWidthPct = stressValue === null ? 0 : Math.min(100, (stressValue / GAUGE_MAX_RATIO) * 100)

  return (
    <MetricCard
      title="Available liquidity"
      provenance={liquidity.available_liquidity.provenance}
      footer={liquidity.available_liquidity.note}
    >
      <p className="text-2xl font-semibold text-slate-800 tabular-nums">
        {formatAmountCompact(liquidity.available_liquidity.value)}
      </p>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium tracking-wide text-slate-400 uppercase">Liquidity stress</span>
          {stressValue !== null && <span className="font-semibold text-slate-700 tabular-nums">{formatRatio(stressValue)}×</span>}
        </div>
        {stressValue === null ? (
          <p className="mt-2 text-xs text-slate-400">{liquidity.liquidity_stress.note}</p>
        ) : (
          <>
            <div
              className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100"
              role="img"
              aria-label={`Liquidity stress ratio ${formatRatio(stressValue)}, where 1.0 means estimated exposure equals available liquidity`}
            >
              <div
                className={`h-full rounded-full ${stressValue >= 1 ? 'bg-red-500' : stressValue >= 0.5 ? 'bg-amber-500' : 'bg-teal-500'}`}
                style={{ width: `${barWidthPct}%` }}
              />
            </div>
            <p className="mt-1.5 text-[11px] text-slate-400">
              100% = estimated exposure would equal available liquidity. {liquidity.liquidity_stress.note}
            </p>
          </>
        )}
      </div>
    </MetricCard>
  )
}
