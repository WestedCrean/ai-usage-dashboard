import { type ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  subValue?: string
  icon?: ReactNode
  delta?: number       // percent change, e.g. +12.4 or -5.1
  accentColor?: string // tailwind text colour class
}

export function StatCard({ label, value, subValue, icon, delta, accentColor = 'text-[#6366f1]' }: StatCardProps) {
  const deltaPositive = delta !== undefined && delta > 0
  const deltaZero = delta === undefined || delta === 0
  const deltaAbs = delta !== undefined ? Math.abs(delta).toFixed(1) : null

  return (
    <div className="card-neo p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-[#7a8fb5]">
          {label}
        </span>
        {icon && (
          <span className={`${accentColor} opacity-70`}>{icon}</span>
        )}
      </div>

      <div>
        <div className={`text-3xl font-bold ${accentColor}`}>{value}</div>
        {subValue && (
          <div className="text-xs text-[#7a8fb5] mt-0.5">{subValue}</div>
        )}
      </div>

      {delta !== undefined && (
        <div className={`flex items-center gap-1 text-xs font-semibold ${
          deltaZero  ? 'text-[#7a8fb5]' :
          deltaPositive ? 'text-[#10b981]' : 'text-[#ef4444]'
        }`}>
          {deltaZero ? <Minus size={12} /> : deltaPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {deltaAbs}% vs last period
        </div>
      )}
    </div>
  )
}
