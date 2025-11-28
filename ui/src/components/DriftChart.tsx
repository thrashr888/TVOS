import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

export function DriftChart() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['drift-history'],
    queryFn: () => api.getDriftHistory(50),
    refetchInterval: 60000,
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading drift history...</div>
  }

  const history = data || []
  // Reverse to show oldest to newest left to right
  const chartData = [...history].reverse().map((d: any) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleTimeString(),
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
            <TrendingUp className="h-5 w-5 text-orange-500" />
            Semantic Drift Timeline
          </h2>
          <p className="text-sm text-muted-foreground">
            Tracking conceptual shifts in system behavior over time.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="rounded-lg p-2 transition-colors hover:bg-white/5"
        >
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>

      <div className="glass h-[400px] rounded-xl border border-white/5 p-6">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#ffffff40"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#ffffff40"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[0, 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                border: '1px solid #ffffff10',
                borderRadius: '8px',
              }}
              itemStyle={{ color: '#fff' }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, fill: '#f97316' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
