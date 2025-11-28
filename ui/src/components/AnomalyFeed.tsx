import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

export function AnomalyFeed() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['anomalies'],
    queryFn: api.getAnomalies,
    refetchInterval: 30000,
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading anomalies...</div>
  }

  const anomalies = data?.anomalies || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Semantic Anomalies
          </h2>
          <p className="text-sm text-muted-foreground">
            Events that deviate significantly from the norm, explained by AI.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="rounded-lg p-2 transition-colors hover:bg-white/5"
        >
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>

      <div className="grid gap-4">
        {anomalies.length === 0 ? (
          <div className="glass rounded-xl border border-white/5 p-8 text-center">
            <p className="text-muted-foreground">No anomalies detected in the last hour.</p>
          </div>
        ) : (
          anomalies.map((anomaly: any) => (
            <div
              key={anomaly.event_id}
              className="glass rounded-xl border border-red-500/20 bg-red-500/5 p-6"
            >
              <div className="flex items-start gap-4">
                <div className="rounded-lg bg-red-500/10 p-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-red-400">
                      {typeof anomaly.event_id === 'string' ? anomaly.event_id.slice(0, 8) : 'Unknown'}
                    </span>
                    <span className="rounded-full border border-red-500/20 bg-red-500/10 px-2 py-1 text-xs text-red-400">
                      Score: {Math.abs(anomaly.score || -1).toFixed(2)}
                    </span>
                  </div>

                  <div className="rounded-lg border border-white/5 bg-black/20 p-3">
                    <p className="line-clamp-2 font-mono text-sm text-white/80">
                      {anomaly.text || 'No text payload'}
                    </p>
                  </div>

                  <div className="mt-4">
                    <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-blue-400">
                      AI Explanation
                    </h4>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {anomaly.explanation}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
