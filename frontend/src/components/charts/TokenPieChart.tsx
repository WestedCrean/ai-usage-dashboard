import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

interface TokenData {
  name: string
  value: number
}

interface TokenPieChartProps {
  inputTokens: number
  outputTokens: number
}

const COLORS = ['#6366f1', '#8b5cf6']

const formatTokens = (v: number) =>
  v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M`
  : v >= 1_000 ? `${(v / 1_000).toFixed(1)}K`
  : String(v)

export function TokenPieChart({ inputTokens, outputTokens }: TokenPieChartProps) {
  const data: TokenData[] = [
    { name: 'Input', value: inputTokens },
    { name: 'Output', value: outputTokens },
  ]

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={4}
          dataKey="value"
          label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [formatTokens(Number(value)), 'Tokens']}
          contentStyle={{
            background: 'rgba(248,250,252,0.92)',
            border: '1px solid rgba(168,185,209,0.4)',
            borderRadius: '0.75rem',
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" iconSize={8} />
      </PieChart>
    </ResponsiveContainer>
  )
}
