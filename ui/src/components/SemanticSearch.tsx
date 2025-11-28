import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Search, Sparkles } from 'lucide-react'

interface SemanticSearchProps {
  externalQuery?: string
}

const EXAMPLES = [
  'High CPU usage processes',
  'Git commit undo commands',
  'React hooks documentation',
  'Database connection timeouts',
  'Suspicious network scans',
]

export function SemanticSearch({ externalQuery }: SemanticSearchProps) {
  const [query, setQuery] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  // Sync with external query
  useEffect(() => {
    if (externalQuery) {
      setQuery(externalQuery)
      setSearchQuery(externalQuery)
    }
  }, [externalQuery])

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => api.searchSimilar(searchQuery, 10),
    enabled: searchQuery.length > 0,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(query)
  }

  const handleExampleClick = (example: string) => {
    setQuery(example)
    setSearchQuery(example)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Semantic Search</h2>
        <p className="text-muted-foreground">Find similar events using vector embeddings</p>
      </div>

      <div className="space-y-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe what you are looking for..."
              className="glass w-full rounded-lg bg-white/5 py-3 pl-12 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>
          <button
            type="submit"
            className="glow rounded-lg bg-gradient-to-r from-blue-500 to-orange-500 px-6 py-3 font-medium transition-opacity hover:opacity-90"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-2">
          <span className="flex items-center gap-1 py-1 text-sm text-muted-foreground">
            <Sparkles className="h-3 w-3" /> Try:
          </span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => handleExampleClick(example)}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-blue-200 transition-colors hover:bg-white/10"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="py-12 text-center text-muted-foreground">Searching...</div>}

      {results && (
        <div className="space-y-2">
          {results.map((result: any, idx: number) => (
            <div
              key={result.event_id || idx}
              className="glass rounded-lg p-4 transition-all hover:bg-white/5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-3">
                    <span className="rounded bg-blue-500/10 px-2 py-1 font-mono text-xs text-blue-400">
                      Score: {(1 - result.score).toFixed(3)}
                    </span>
                    {result.payload?.source && (
                      <span className="text-xs text-muted-foreground">{result.payload.source}</span>
                    )}
                  </div>
                  <p className="text-sm text-foreground">
                    {result.payload?.text || 'No text available'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {results && results.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          No results found. Try a different query.
        </div>
      )}
    </div>
  )
}
