const API_BASE = import.meta.env.VITE_API_URL || '/api'

export interface Event {
  event_id: string
  timestamp_ms: number
  source: string
  text_payload: string
  metrics?: Record<string, number>
}

export interface DriftMetrics {
  drift_score: number
  window1_count: number
  window2_count: number
  window_hours: number
}

export interface ClusterInfo {
  cluster_count: number
  total_events: number
  noise_count: number
  clusters: Record<number, string[]>
}

export interface StatsInfo {
  window_hours: number
  event_count: number
  avg_metrics: Record<string, number>
  timestamp: number
}

export const api = {
  async getStats() {
    return fetchWithCheck(`${API_BASE}/stats`)
  },

  async getRecentEvents(limit = 50) {
    const now = Date.now()
    const oneHourAgo = now - 60 * 60 * 1000
    const data = await fetchWithCheck(
      `${API_BASE}/query/window?start_ms=${oneHourAgo}&end_ms=${now}&limit=${limit}`
    )
    return data.events as Event[]
  },

  async searchSimilar(query: string, limit = 10) {
    const res = await fetch(`${API_BASE}/query/similarity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: query, limit }),
    })
    if (!res.ok) throw new Error('Search failed')
    return res.json()
  },

  async getDrift(): Promise<DriftMetrics> {
    return fetchWithCheck(`${API_BASE}/analytics/drift`)
  },

  async getClusters(): Promise<ClusterInfo> {
    return fetchWithCheck(`${API_BASE}/analytics/clusters`)
  },

  async getWindowStats(): Promise<StatsInfo> {
    return fetchWithCheck(`${API_BASE}/analytics/stats`)
  },

  async getDriftHistory(limit = 100) {
    return fetchWithCheck(`${API_BASE}/analytics/drift/history?limit=${limit}`)
  },

  async getAnomalies() {
    return fetchWithCheck(`${API_BASE}/analytics/anomalies`)
  },

  async getEmbeddingProjection(windowHours = 1, method = 'pca') {
    return fetchWithCheck(
      `${API_BASE}/analytics/embeddings/projection?window_hours=${windowHours}&method=${method}`
    )
  },

  async runTVQL(query: string) {
    const res = await fetch(`${API_BASE}/query/tvql`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'TVQL Error')
    }
    return res.json()
  },
}

async function fetchWithCheck(url: string) {
  const res = await fetch(url)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}
