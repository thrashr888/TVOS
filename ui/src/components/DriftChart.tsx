import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { TrendingUp } from 'lucide-react';

export function DriftChart() {
    const { data: drift, isLoading } = useQuery({
        queryKey: ['drift'],
        queryFn: () => api.getDrift(),
        refetchInterval: 10000,
    });

    const { data: stats } = useQuery({
        queryKey: ['stats'],
        queryFn: () => api.getWindowStats(),
        refetchInterval: 10000,
    });

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-foreground">Semantic Drift Analysis</h2>
                <p className="text-muted-foreground">
                    Detect semantic drift by comparing embedding centroids across time windows
                </p>
            </div>

            {isLoading && (
                <div className="text-center py-12 text-muted-foreground">Loading drift data...</div>
            )}

            {drift && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="glass rounded-lg p-6">
                        <div className="flex items-center gap-3 mb-2">
                            <TrendingUp className="w-5 h-5 text-purple-400" />
                            <h3 className="text-sm font-medium text-muted-foreground">Drift Score</h3>
                        </div>
                        <p className="text-3xl font-bold text-foreground">
                            {drift.drift_score?.toFixed(4) || '0.0000'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Cosine distance between windows</p>
                    </div>

                    <div className="glass rounded-lg p-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Window 1</h3>
                        <p className="text-3xl font-bold text-foreground">{drift.window1_count || 0}</p>
                        <p className="text-xs text-muted-foreground mt-1">Events in previous window</p>
                    </div>

                    <div className="glass rounded-lg p-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Window 2</h3>
                        <p className="text-3xl font-bold text-foreground">{drift.window2_count || 0}</p>
                        <p className="text-xs text-muted-foreground mt-1">Events in current window</p>
                    </div>
                </div>
            )}

            {stats && (
                <div className="glass rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-foreground mb-4">Window Statistics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Events</p>
                            <p className="text-2xl font-bold text-foreground">{stats.event_count}</p>
                        </div>
                        {stats.avg_metrics && Object.entries(stats.avg_metrics).map(([key, value]) => (
                            <div key={key}>
                                <p className="text-sm text-muted-foreground">{key} (avg)</p>
                                <p className="text-2xl font-bold text-foreground">{value.toFixed(2)}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
