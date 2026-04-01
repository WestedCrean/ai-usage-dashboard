import { useState, useMemo } from 'react'
import { Activity, DollarSign, Zap, Clock } from 'lucide-react'
import { format, parseISO } from 'date-fns'

import { StatCard } from '../components/dashboard/StatCard'
import { ChartCard } from '../components/dashboard/ChartCard'
import { FilterPanel, type FilterValues } from '../components/dashboard/FilterPanel'
import { UsageLineChart } from '../components/charts/UsageLineChart'
import { CostBarChart } from '../components/charts/CostBarChart'
import { TokenPieChart } from '../components/charts/TokenPieChart'
import { Badge } from '../components/ui/Badge'

import { useUsageSummary } from '../hooks/useUsageSummary'
import { useUsage } from '../hooks/useUsage'
import { useModels } from '../hooks/useModels'
import { useProjects } from '../hooks/useProjects'

const EMPTY_FILTERS: FilterValues = { model: '', project: '', team: '', from: '', to: '' }

function formatNumber(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function LoadingCard() {
  return (
    <div className="card-neo p-5 h-28 animate-pulse">
      <div className="h-3 w-24 bg-[#c4d1e0] rounded mb-3" />
      <div className="h-8 w-32 bg-[#c4d1e0] rounded" />
    </div>
  )
}

interface DashboardPageProps {
  filterOpen: boolean
  onFilterClose: () => void
}

export function DashboardPage({ filterOpen, onFilterClose }: DashboardPageProps) {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS)

  const apiFilters = useMemo(() => ({
    model:   filters.model   || undefined,
    project: filters.project || undefined,
    team:    filters.team    || undefined,
    from:    filters.from    || undefined,
    to:      filters.to      || undefined,
  }), [filters])

  const { data: summary, isLoading: summaryLoading } = useUsageSummary(apiFilters)
  const { data: records = [] }                        = useUsage(apiFilters)
  const { data: models  = [] }                        = useModels()
  const { data: projects = [] }                       = useProjects()

  // ── Derived data for charts ──────────────────────────────────────────────

  // Usage over time — group records by date + model name
  const { lineData, lineModels } = useMemo(() => {
    const modelMap = Object.fromEntries(models.map(m => [m.id, m.name]))
    const byDate: Record<string, Record<string, number>> = {}

    for (const r of records) {
      const date = format(parseISO(r.timestamp), 'yyyy-MM-dd')
      const name = modelMap[r.model_id] ?? `Model #${r.model_id}`
      byDate[date] ??= {}
      byDate[date][name] = (byDate[date][name] ?? 0) + 1
    }

    const dates = Object.keys(byDate).sort()
    const modelNames = [...new Set(records.map(r => modelMap[r.model_id] ?? `Model #${r.model_id}`))]
    const lineData = dates.map(date => ({ date, ...byDate[date] }))

    return { lineData, lineModels: modelNames }
  }, [records, models])

  // Cost by model
  const costData = useMemo(() => {
    const modelMap = Object.fromEntries(models.map(m => [m.id, m.name]))
    const byCost: Record<string, number> = {}
    for (const r of records) {
      const name = modelMap[r.model_id] ?? `Model #${r.model_id}`
      byCost[name] = (byCost[name] ?? 0) + r.cost
    }
    return Object.entries(byCost).map(([model, cost]) => ({ model, cost }))
  }, [records, models])

  // Filter options
  const modelOptions = models.map(m => ({ value: m.name, label: `${m.provider} / ${m.name}` }))
  const projectOptions = projects.map(p => ({ value: p.name, label: p.name }))
  const teamOptions = [...new Set(projects.map(p => p.team).filter(Boolean))]
    .map(t => ({ value: t, label: t }))

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  return (
    <>
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-[#1a2942]">Dashboard</h1>
          <p className="text-xs text-[#7a8fb5] mt-0.5">AI model usage overview</p>
        </div>
        {activeFiltersCount > 0 && (
          <Badge color="indigo">{activeFiltersCount} filter{activeFiltersCount > 1 ? 's' : ''} active</Badge>
        )}
      </div>

      {/* ── Stat cards ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => <LoadingCard key={i} />)
        ) : (
          <>
            <StatCard
              label="Total Calls"
              value={formatNumber(summary?.total_calls ?? 0)}
              icon={<Activity size={18} />}
              accentColor="text-[#6366f1]"
            />
            <StatCard
              label="Total Tokens"
              value={formatNumber(summary?.total_tokens ?? 0)}
              subValue={`${formatNumber(summary?.total_input_tokens ?? 0)} in / ${formatNumber(summary?.total_output_tokens ?? 0)} out`}
              icon={<Zap size={18} />}
              accentColor="text-[#8b5cf6]"
            />
            <StatCard
              label="Total Cost"
              value={`$${(summary?.total_cost ?? 0).toFixed(2)}`}
              icon={<DollarSign size={18} />}
              accentColor="text-[#10b981]"
            />
            <StatCard
              label="Avg Latency"
              value={summary?.avg_latency_ms != null ? `${Math.round(summary.avg_latency_ms)}ms` : '—'}
              subValue={summary?.success_rate != null ? `${(summary.success_rate * 100).toFixed(1)}% success` : undefined}
              icon={<Clock size={18} />}
              accentColor="text-[#f59e0b]"
            />
          </>
        )}
      </div>

      {/* ── Charts row ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <ChartCard
          title="API Calls Over Time"
          subtitle="Calls per day by model"
          className="lg:col-span-2"
        >
          {lineData.length > 0 ? (
            <UsageLineChart data={lineData} models={lineModels} />
          ) : (
            <EmptyChart message="No usage records in selected range" />
          )}
        </ChartCard>

        <ChartCard title="Token Breakdown" subtitle="Input vs output tokens">
          <TokenPieChart
            inputTokens={summary?.total_input_tokens ?? 0}
            outputTokens={summary?.total_output_tokens ?? 0}
          />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Cost by Model" subtitle="Accumulated spend per model">
          {costData.length > 0 ? (
            <CostBarChart data={costData} />
          ) : (
            <EmptyChart message="No cost data in selected range" />
          )}
        </ChartCard>

        {/* Model registry quick view */}
        <ChartCard title="Registered Models" subtitle={`${models.length} model${models.length !== 1 ? 's' : ''}`}>
          {models.length === 0 ? (
            <EmptyChart message="No models registered yet" />
          ) : (
            <div className="flex flex-col gap-2">
              {models.slice(0, 6).map(m => (
                <div key={m.id} className="flex items-center justify-between py-2 border-b border-[#dce4ec] last:border-0">
                  <div>
                    <span className="text-sm font-medium text-[#1a2942]">{m.name}</span>
                    <span className="text-xs text-[#7a8fb5] ml-2">{m.provider}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-[#7a8fb5]">
                      ${m.cost_per_input_token.toFixed(6)}&nbsp;<span className="text-[#a8b9d1]">/&nbsp;in</span>
                    </div>
                    <div className="text-xs text-[#7a8fb5]">
                      ${m.cost_per_output_token.toFixed(6)}&nbsp;<span className="text-[#a8b9d1]">/&nbsp;out</span>
                    </div>
                  </div>
                </div>
              ))}
              {models.length > 6 && (
                <p className="text-xs text-[#7a8fb5] text-center pt-1">+{models.length - 6} more</p>
              )}
            </div>
          )}
        </ChartCard>
      </div>

      {/* ── Filter panel ──────────────────────────────────────────────────── */}
      <FilterPanel
        open={filterOpen}
        onClose={onFilterClose}
        values={filters}
        onChange={setFilters}
        modelOptions={modelOptions}
        projectOptions={projectOptions}
        teamOptions={teamOptions}
      />
    </>
  )
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="h-52 flex items-center justify-center text-sm text-[#a8b9d1]">
      {message}
    </div>
  )
}
