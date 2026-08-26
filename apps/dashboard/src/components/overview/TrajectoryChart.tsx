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

interface ChartPoint {
  date: string
  gmv: number
  chargebackRateAvg: number
  refundRateAvg: number
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-slate-700">{label ? formatShortDate(label) : ''}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-slate-500">
          {entry.name}:{' '}
          <span className="font-medium text-slate-700">
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
    return <p className="py-10 text-center text-sm text-slate-400">No observation history available.</p>
  }

  const firstDate = data[0].date
  const lastDate = data[data.length - 1].date

  return (
    <div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              minTickGap={40}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={false}
            />
            <YAxis
              yAxisId="gmv"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            />
            <YAxis
              yAxisId="rate"
              orientation="right"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              width={44}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              yAxisId="gmv"
              type="monotone"
              dataKey="gmv"
              name="GMV"
              stroke="#4338ca"
              fill="#4338ca"
              fillOpacity={0.08}
              strokeWidth={1.75}
            />
            <Line
              yAxisId="rate"
              type="monotone"
              dataKey="chargebackRateAvg"
              name="Chargeback rate (7d avg)"
              stroke="#dc2626"
              strokeWidth={1.75}
              dot={false}
            />
            <Line
              yAxisId="rate"
              type="monotone"
              dataKey="refundRateAvg"
              name="Refund rate (7d avg)"
              stroke="#d97706"
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 3"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <LegendSwatch color="#4338ca" label="GMV (observed)" />
        <LegendSwatch color="#dc2626" label="Chargeback rate, 7d avg (observed)" />
        <LegendSwatch color="#d97706" label="Refund rate, 7d avg (observed)" dashed />
      </div>
      <p className="mt-2 text-[11px] text-slate-400">
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
