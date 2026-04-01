import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

interface CostDataPoint {
  model: string
  cost: number
}

interface CostBarChartProps {
  data: CostDataPoint[]
}

export function CostBarChart({ data }: CostBarChartProps) {
  const formatCost = (v: number) => `$${v.toFixed(2)}`

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(168,185,209,0.35)" vertical={false} />
        <XAxis
          dataKey="model"
          tick={{ fontSize: 11, fill: '#7a8fb5' }}
          axisLine={{ stroke: '#a8b9d1' }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatCost}
          tick={{ fontSize: 11, fill: '#7a8fb5' }}
          axisLine={false}
          tickLine={false}
          width={48}
        />
        <Tooltip
          formatter={(value) => [formatCost(Number(value)), 'Cost']}
          contentStyle={{
            background: 'rgba(248,250,252,0.92)',
            border: '1px solid rgba(168,185,209,0.4)',
            borderRadius: '0.75rem',
            fontSize: 12,
          }}
        />
        <Bar
          dataKey="cost"
          fill="#6366f1"
          radius={[6, 6, 0, 0]}
          maxBarSize={48}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
