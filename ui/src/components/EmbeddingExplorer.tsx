import { useQuery } from '@tanstack/react-query'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Network, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { useState } from 'react'

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']

export function EmbeddingExplorer() {
  const [method, setMethod] = useState('pca')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['projection', method],
    queryFn: () => api.getEmbeddingProjection(1, method),
    refetchInterval: 60000,
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Computing projection...</div>
  }

  const points = data || []

  // Assign colors based on source
  const sources = [...new Set(points.map((p: any) => p.source))]
  const getColor = (source: string) => COLORS[sources.indexOf(source) % COLORS.length]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
            <Network className="h-5 w-5 text-purple-500" />
            Embedding Explorer
          </h2>
          <p className="text-sm text-muted-foreground">
            2D visualization of semantic event space. Closer points = similar meaning.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="rounded-md border border-white/10 bg-white/5 px-2 py-1 text-sm text-white focus:outline-none"
          >
            <option value="pca">PCA</option>
            <option value="umap">UMAP</option>
          </select>
          <button
            onClick={() => refetch()}
            className="rounded-lg p-2 transition-colors hover:bg-white/5"
          >
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      <div className="glass h-[500px] rounded-xl border border-white/5 p-6">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <XAxis type="number" dataKey="x" name="X" hide />
            <YAxis type="number" dataKey="y" name="Y" hide />
            <ZAxis type="number" range={[50, 50]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="glass rounded-lg border border-white/10 p-3 shadow-xl">
                      <p className="mb-1 font-mono text-xs text-blue-400">{data.source}</p>
                      <p className="text-xs text-white/80">{data.event_id}</p>
                    </div>
                  )
                }
                return null
              }}
            />
            <Scatter name="Events" data={points} fill="#8884d8">
              {points.map((entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.source)} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap gap-4">
        {sources.map((source: any) => (
          <div key={source} className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: getColor(source) }} />
            <span className="text-xs text-muted-foreground">{source}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
