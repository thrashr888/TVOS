const API_BASE = import.meta.env.VITE_API_URL || '/api';

export interface Event {
    event_id: string;
    timestamp_ms: number;
    source: string;
    text_payload: string;
    metrics?: Record<string, number>;
}

export interface DriftMetrics {
    drift_score: number;
    window1_count: number;
    window2_count: number;
    window_hours: number;
}

export interface ClusterInfo {
    cluster_count: number;
    total_events: number;
    noise_count: number;
    clusters: Record<number, string[]>;
}

export interface StatsInfo {
    window_hours: number;
    event_count: number;
    avg_metrics: Record<string, number>;
    timestamp: number;
}

export const api = {
    async getStats() {
        const res = await fetch(`${API_BASE}/stats`);
        return res.json();
    },

    async getRecentEvents(limit = 50) {
        const now = Date.now();
        const oneHourAgo = now - (60 * 60 * 1000);
        const res = await fetch(
            `${API_BASE}/query/window?start_ms=${oneHourAgo}&end_ms=${now}&limit=${limit}`
        );
        const data = await res.json();
        return data.events as Event[];
    },

    async searchSimilar(query: string, limit = 10) {
        const res = await fetch(`${API_BASE}/query/similarity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ q: query, limit }),
        });
        return res.json();
    },

    async getDrift(): Promise<DriftMetrics> {
        const res = await fetch(`${API_BASE}/analytics/drift`);
        return res.json();
    },

    async getClusters(): Promise<ClusterInfo> {
        const res = await fetch(`${API_BASE}/analytics/clusters`);
        return res.json();
    },

    async getWindowStats(): Promise<StatsInfo> {
        const res = await fetch(`${API_BASE}/analytics/stats`);
        return res.json();
    },
};
