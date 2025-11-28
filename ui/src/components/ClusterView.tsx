import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Network } from 'lucide-react'

export function ClusterView() {
  const { data: clusters, isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: () => api.getClusters(),
    refetchInterval: 15000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Vector Clustering</h2>
        <p className="text-muted-foreground">HDBSCAN clustering of embeddings over time</p>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-muted-foreground">Loading cluster data...</div>
      )}

      {clusters && clusters.clusters && Object.keys(clusters.clusters).length > 0 && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(clusters.clusters).map(([id, info]: [string, any]) => (
            <div
              key={id}
              className="glass rounded-xl border border-white/5 p-6 transition-all hover:border-blue-500/30"
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <Network className="h-5 w-5 text-blue-400" />
                </div>
                <span className="rounded-full bg-white/5 px-2 py-1 font-mono text-xs text-muted-foreground">
                  Cluster {id}
                </span>
              </div>

              <h3 className="mb-2 line-clamp-2 text-lg font-semibold text-white">
                {info.topic || `Topic ${id}`}
              </h3>

              <div className="mb-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Events</span>
                  <span className="font-mono text-white">{info.count || info.length || 0}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {clusters && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="glass rounded-lg p-6">
            <div className="mb-2 flex items-center gap-3">
              <Network className="h-5 w-5 text-purple-400" />
              <h3 className="text-sm font-medium text-muted-foreground">Clusters Detected</h3>
            </div>
            <p className="text-3xl font-bold text-foreground">{clusters.cluster_count || 0}</p>
          </div>

          <div className="glass rounded-lg p-6">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">Total Events</h3>
            <p className="text-3xl font-bold text-foreground">{clusters.total_events || 0}</p>
          </div>

          <div className="glass rounded-lg p-6">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">Noise Points</h3>
            <p className="text-3xl font-bold text-foreground">{clusters.noise_count || 0}</p>
          </div>
        </div>
      )}

      {clusters && clusters.clusters && Object.keys(clusters.clusters).length > 0 && (
        <div className="glass rounded-lg p-6">
          <h3 className="mb-4 text-lg font-semibold text-foreground">Cluster Details</h3>
          <div className="space-y-4">
            {Object.entries(clusters.clusters).map(([clusterId, eventIds]) => (
              <div key={clusterId} className="border-l-2 border-purple-500 pl-4">
                <h4 className="mb-2 text-sm font-medium text-purple-400">
                  Cluster {clusterId} ({Array.isArray(eventIds) ? eventIds.length : 0} events)
                </h4>
                <div className="flex flex-wrap gap-2">
                  {Array.isArray(eventIds) && eventIds.slice(0, 10).map((eventId) => (
                    <span
                      key={eventId}
                      className="rounded bg-white/5 px-2 py-1 font-mono text-xs text-muted-foreground"
                    >
                      {typeof eventId === 'string' ? eventId.slice(0, 8) : String(eventId).slice(0, 8)}...
                    </span>
                  ))}
                  {Array.isArray(eventIds) && eventIds.length > 10 && (
                    <span className="text-xs text-muted-foreground">
                      +{eventIds.length - 10} more
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {clusters && clusters.cluster_count === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          No clusters detected. Try sending more events with varied content.
        </div>
      )}
    </div>
  )
}
