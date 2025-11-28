import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Activity, TrendingUp, Network, Server } from 'lucide-react'
import { MetricChart } from './MetricChart'
import { DriftChart } from './DriftChart'

export function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 30000,
  })

  const { data: drift } = useQuery({
    queryKey: ['drift'],
    queryFn: () => api.getDrift(),
    refetchInterval: 30000,
  })

  const { data: clusters } = useQuery({
    queryKey: ['clusters'],
    queryFn: () => api.getClusters(),
    refetchInterval: 30000,
  })

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="glass flex items-center gap-4 rounded-lg p-4">
          <div className="rounded-full bg-blue-500/20 p-3 text-blue-400">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Events</p>
            <p className="text-2xl font-bold text-foreground">
              {stats?.event_count?.toLocaleString() || 0}
            </p>
          </div>
        </div>

        <div className="glass flex items-center gap-4 rounded-lg p-4">
          <div className="rounded-full bg-orange-500/20 p-3 text-orange-400">
            <TrendingUp className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Drift Score</p>
            <p className="text-2xl font-bold text-foreground">
              {drift?.drift_score?.toFixed(4) || '0.0000'}
            </p>
          </div>
        </div>

        <div className="glass flex items-center gap-4 rounded-lg p-4">
          <div className="rounded-full bg-purple-500/20 p-3 text-purple-400">
            <Network className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Clusters</p>
            <p className="text-2xl font-bold text-foreground">{clusters?.cluster_count || 0}</p>
          </div>
        </div>

        <div className="glass flex items-center gap-4 rounded-lg p-4">
          <div className="rounded-full bg-green-500/20 p-3 text-green-400">
            <Server className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">System Status</p>
            <p className="text-lg font-bold text-foreground">Operational</p>
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="h-80">
          <MetricChart
            title="System Load (CPU & Memory)"
            metrics={['cpu_percent', 'memory_percent']}
            colors={['#3b82f6', '#f97316']}
          />
        </div>
        <div className="h-80">
          <DriftChart />
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="h-80">
          <MetricChart
            title="Network Activity (KB/s)"
            metrics={['bytes_sent', 'bytes_recv']}
            colors={['#10b981', '#8b5cf6']}
          />
        </div>
        {/* Placeholder for another chart or list */}
        <div className="glass h-80 rounded-lg p-6">
          <h3 className="mb-4 text-lg font-medium text-foreground">Recent Anomalies</h3>
          <div className="flex h-full flex-col justify-center text-center text-muted-foreground">
            No anomalies detected in the last hour.
          </div>
        </div>
      </div>
    </div>
  )
}
