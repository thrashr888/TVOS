import { useState } from 'react'
import { Terminal, Play, Loader2, Sparkles } from 'lucide-react'
import { api } from '../lib/api'

const EXAMPLES = [
  'FIND similar("database error") IN last 1h',
  'FIND similar("security breach") IN last 24h WHERE cpu > 80',
  'FIND similar("memory leak") IN last 6h',
  'FIND similar("failed login") IN last 1h',
  'FIND similar("payment failure") IN last 7d',
  'FIND similar("latency spike") IN last 1h WHERE memory > 90',
]

export function TVQLConsole() {
  const [query, setQuery] = useState('FIND similar("error") IN last 1h WHERE cpu > 50')
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleRun = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.runTVQL(query)
      setResults(data.results || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
            <Terminal className="h-5 w-5 text-green-500" />
            TVQL Console
          </h2>
          <p className="text-sm text-muted-foreground">
            Execute temporal-semantic queries against the event store.
          </p>
        </div>
      </div>

      <div className="glass space-y-4 rounded-xl border border-white/5 p-4">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-32 w-full resize-none rounded-lg border border-white/10 bg-black/50 p-4 font-mono text-sm text-green-400 focus:border-green-500/50 focus:outline-none"
            spellCheck={false}
          />
          <button
            onClick={handleRun}
            disabled={loading}
            className="absolute bottom-4 right-4 flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-500 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run Query
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="flex items-center gap-1 py-1 text-sm text-muted-foreground">
            <Sparkles className="h-3 w-3" /> Try:
          </span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => setQuery(example)}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs text-green-200 transition-colors hover:bg-white/10"
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 font-mono text-sm text-red-400">
            Error: {error}
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Results ({results.length})
            </h3>
            <div className="custom-scrollbar max-h-[400px] space-y-2 overflow-y-auto pr-2">
              {results.map((event) => (
                <div
                  key={event.event_id}
                  className="rounded-lg border border-white/5 bg-white/5 p-3 transition-colors hover:border-white/10"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-mono text-xs text-blue-400">{event.source}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(event.timestamp_ms).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="font-mono text-sm text-white/90">{event.text_payload}</p>
                  {event.metrics && (
                    <div className="mt-2 flex gap-2">
                      {Object.entries(JSON.parse(event.metrics)).map(([k, v]) => (
                        <span
                          key={k}
                          className="rounded bg-white/5 px-2 py-0.5 text-xs text-muted-foreground"
                        >
                          {k}: {String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
