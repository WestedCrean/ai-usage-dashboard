import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

interface DataPoint {
  date: string
  [model: string]: string | number
}

interface UsageLineChartProps {
  data: DataPoint[]
  models: string[]
}

const COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#3b82f6']

export function UsageLineChart({ data, models }: UsageLineChartProps) {
  const formatDate = (value: string) => {
    try { return format(new Date(value), 'MMM d') }
    catch { return value }
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(168,185,209,0.35)" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: '#7a8fb5' }}
          axisLine={{ stroke: '#a8b9d1' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#7a8fb5' }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            background: 'rgba(248,250,252,0.92)',
            border: '1px solid rgba(168,185,209,0.4)',
            borderRadius: '0.75rem',
            fontSize: 12,
          }}
          labelFormatter={(label) => formatDate(String(label))}
        />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: '12px' }}
          iconType="circle"
          iconSize={8}
        />
        {models.map((model, i) => (
          <Line
            key={model}
            type="monotone"
            dataKey={model}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
