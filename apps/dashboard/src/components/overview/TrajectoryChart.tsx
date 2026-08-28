import { useMemo } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ObservationRecord } from '@/api/types'
import { formatShortDate } from '@/lib/format'
import { trailingMovingAverage } from '@/lib/chartUtils'

const MOVING_AVERAGE_WINDOW = 7

// Chart accent palette — the primary (GMV) series deliberately uses the
// same electric purple-blue family as the brand accent (nav glow, logo),
// so the chart reads as part of one coherent identity; the two secondary
// rate lines stay in their existing, distinct red/amber status colors so
// a reader never confuses "this is the GMV line" with a risk signal.
const GMV_COLOR = '#818cf8' // indigo-400 — restrained electric purple-blue for the primary series
const CHARGEBACK_COLOR = '#f87171' // red-400 — brightened for legibility on a dark surface
const REFUND_COLOR = '#fbbf24' // amber-400
const GRID_COLOR = '#1c2029' // matches --color-border-subtle
const AXIS_LINE_COLOR = '#242938' // matches --color-border
const AXIS_TICK_COLOR = '#8b93a7'

interface ChartPoint {
  date: string
  gmv: number
  chargebackRateAvg: number
  refundRateAvg: number
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg shadow-black/40">
      <p className="mb-1 font-medium text-foreground">{label ? formatShortDate(label) : ''}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-secondary-foreground">
          {entry.name}:{' '}
          <span className="font-medium text-foreground">
            {entry.name === 'GMV' ? Math.round(entry.value).toLocaleString() : `${(entry.value * 100).toFixed(2)}%`}
          </span>
        </p>
      ))}
    </div>
  )
}

export function TrajectoryChart({ observations }: { observations: ObservationRecord[] }) {
  const data = useMemo<ChartPoint[]>(() => {
    const sorted = [...observations].sort((a, b) => a.day_index - b.day_index)
    const chargebackAvg = trailingMovingAverage(
      sorted.map((o) => o.chargeback_rate),
      MOVING_AVERAGE_WINDOW,
    )
    const refundAvg = trailingMovingAverage(
      sorted.map((o) => o.refund_rate),
      MOVING_AVERAGE_WINDOW,
    )
    return sorted.map((o, i) => ({
      date: o.date,
      gmv: o.gmv,
      chargebackRateAvg: chargebackAvg[i],
      refundRateAvg: refundAvg[i],
    }))
  }, [observations])

  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No observation history available.</p>
  }

  const firstDate = data[0].date
  const lastDate = data[data.length - 1].date

  return (
    <div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="trajectoryGmvFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={GMV_COLOR} stopOpacity={0.22} />
                <stop offset="100%" stopColor={GMV_COLOR} stopOpacity={0.02} />
              </linearGradient>
              {/* Very subtle glow behind the primary (GMV) line only — kept
                  faint on purpose so it reads as "premium," not "neon". */}
              <filter id="trajectoryGmvGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              tick={{ fontSize: 11, fill: AXIS_TICK_COLOR }}
              minTickGap={40}
              axisLine={{ stroke: AXIS_LINE_COLOR }}
              tickLine={false}
            />
            <YAxis
              yAxisId="gmv"
              tick={{ fontSize: 11, fill: AXIS_TICK_COLOR }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            />
            <YAxis
              yAxisId="rate"
              orientation="right"
              tick={{ fontSize: 11, fill: AXIS_TICK_COLOR }}
              axisLine={false}
              tickLine={false}
              width={44}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: AXIS_LINE_COLOR, strokeWidth: 1 }} />
            <Area
              yAxisId="gmv"
              type="monotone"
              dataKey="gmv"
              name="GMV"
              stroke={GMV_COLOR}
              fill="url(#trajectoryGmvFill)"
              strokeWidth={2}
              isAnimationActive={false}
              style={{ filter: 'url(#trajectoryGmvGlow)' }}
            />
            <Line
              yAxisId="rate"
              type="monotone"
              dataKey="chargebackRateAvg"
              name="Chargeback rate (7d avg)"
              stroke={CHARGEBACK_COLOR}
              strokeWidth={1.75}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="rate"
              type="monotone"
              dataKey="refundRateAvg"
              name="Refund rate (7d avg)"
              stroke={REFUND_COLOR}
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 3"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-secondary-foreground">
        <LegendSwatch color={GMV_COLOR} label="GMV (observed)" />
        <LegendSwatch color={CHARGEBACK_COLOR} label="Chargeback rate, 7d avg (observed)" />
        <LegendSwatch color={REFUND_COLOR} label="Refund rate, 7d avg (observed)" dashed />
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        {formatShortDate(firstDate)}–{formatShortDate(lastDate)} · all series are observed historical data, not model
        predictions. Chargeback/refund rates are shown as a trailing {MOVING_AVERAGE_WINDOW}-day average of the daily
        observed values, since raw daily rates are naturally sparse for lower-volume merchants.
      </p>
    </div>
  )
}

function LegendSwatch({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-0.5 w-4"
        style={{ backgroundColor: dashed ? 'transparent' : color, borderTop: dashed ? `2px dashed ${color}` : undefined }}
      />
      {label}
    </span>
  )
}
