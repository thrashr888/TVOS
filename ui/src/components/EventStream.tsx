import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Event } from '../lib/api'
import { formatRelativeTime } from '../lib/utils'
import { RefreshCw, Clock } from 'lucide-react'

interface EventStreamProps {
  timeRange?: number // 0 for Live, otherwise hours
}

export function EventStream({ timeRange = 0 }: EventStreamProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [realtimeEvents, setRealtimeEvents] = useState<Event[]>([])
  const isLive = timeRange === 0

  // Query for historical data (used for initial load AND historical view)
  const {
    data: historicalEvents,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['events', timeRange],
    queryFn: async () => {
      if (isLive) {
        return api.getRecentEvents(50)
      } else {
        const now = Date.now()
        const start = now - timeRange * 3600 * 1000
        const res = await fetch(`/api/query/window?start_ms=${start}&end_ms=${now}&limit=100`)
        const data = await res.json()
        return data.events as Event[]
      }
    },
    // Refetch automatically only if NOT live (to refresh historical view occasionally)
    refetchInterval: isLive ? false : 30000,
  })

  // WebSocket connection (only if Live)
  useEffect(() => {
    if (!isLive) {
      setIsConnected(false)
      setRealtimeEvents([]) // Clear realtime buffer when switching to history
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/events`

    console.log(`Connecting to WebSocket: ${wsUrl}`)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.event_id) {
          const newEvent = data as Event
          setRealtimeEvents((prev) => [newEvent, ...prev].slice(0, 50))
        }
      } catch (e) {
        console.error('Error parsing WS message', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [isLive])

  // Merge events logic
  let displayEvents: Event[] = []
  if (isLive) {
    // In live mode: Realtime buffer + Historical (deduplicated)
    displayEvents = [...realtimeEvents, ...(historicalEvents || [])]
      .reduce((acc, current) => {
        const x = acc.find((item) => item.event_id === current.event_id)
        if (!x) {
          return acc.concat([current])
        } else {
          return acc
        }
      }, [] as Event[])
      .sort((a, b) => b.timestamp_ms - a.timestamp_ms)
      .slice(0, 50)
  } else {
    // In historical mode: Just historical data
    displayEvents = historicalEvents || []
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-foreground">
            {isLive ? 'Live Event Stream' : 'Historical Events'}
            {isLive ? (
              isConnected ? (
                <span className="relative flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-green-500"></span>
                </span>
              ) : (
                <span className="h-3 w-3 rounded-full bg-red-500" title="Disconnected"></span>
              )
            ) : (
              <span className="flex items-center gap-1 rounded-full bg-white/5 px-2 py-1 text-xs font-normal text-muted-foreground">
                <Clock className="h-3 w-3" /> Past {timeRange}h
              </span>
            )}
          </h2>
          <p className="text-muted-foreground">
            {isLive ? 'Real-time events via WebSocket' : `Events from the last ${timeRange} hours`}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="glass flex items-center gap-2 rounded-lg px-4 py-2 transition-colors hover:bg-white/10"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-muted-foreground">Loading events...</div>
      )}

      <div className="space-y-2">
        {displayEvents.map((event: Event) => (
          <div
            key={event.event_id}
            className="glass group cursor-pointer rounded-lg p-4 transition-all hover:bg-white/5"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-3">
                  <span className="rounded bg-blue-500/10 px-2 py-1 font-mono text-xs text-blue-400">
                    {formatRelativeTime(event.timestamp_ms)}
                  </span>
                  <span className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-muted-foreground">
                    {event.source}
                  </span>
                  {event.metrics && Object.keys(event.metrics).length > 0 && (
                    <div className="flex gap-2">
                      {Object.entries(event.metrics)
                        .slice(0, 3)
                        .map(([k, v]) => (
                          <span key={k} className="text-[10px] text-muted-foreground/70">
                            {k}: {typeof v === 'number' ? v.toFixed(2) : v}
                          </span>
                        ))}
                    </div>
                  )}
                </div>
                <p className="break-words font-mono text-sm text-foreground">
                  {event.text_payload}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {displayEvents.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">No events found.</div>
      )}
    </div>
  )
}
