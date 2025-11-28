import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Network } from 'lucide-react';

export function ClusterView() {
    const { data: clusters, isLoading } = useQuery({
        queryKey: ['clusters'],
        queryFn: () => api.getClusters(),
        refetchInterval: 15000,
    });

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-foreground">Vector Clustering</h2>
                <p className="text-muted-foreground">HDBSCAN clustering of embeddings over time</p>
            </div>

            {isLoading && (
                <div className="text-center py-12 text-muted-foreground">Loading cluster data...</div>
            )}

            {clusters && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="glass rounded-lg p-6">
                        <div className="flex items-center gap-3 mb-2">
                            <Network className="w-5 h-5 text-purple-400" />
                            <h3 className="text-sm font-medium text-muted-foreground">Clusters Detected</h3>
                        </div>
                        <p className="text-3xl font-bold text-foreground">{clusters.cluster_count || 0}</p>
                    </div>

                    <div className="glass rounded-lg p-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Events</h3>
                        <p className="text-3xl font-bold text-foreground">{clusters.total_events || 0}</p>
                    </div>

                    <div className="glass rounded-lg p-6">
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Noise Points</h3>
                        <p className="text-3xl font-bold text-foreground">{clusters.noise_count || 0}</p>
                    </div>
                </div>
            )}

            {clusters && clusters.clusters && Object.keys(clusters.clusters).length > 0 && (
                <div className="glass rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-foreground mb-4">Cluster Details</h3>
                    <div className="space-y-4">
                        {Object.entries(clusters.clusters).map(([clusterId, eventIds]) => (
                            <div key={clusterId} className="border-l-2 border-purple-500 pl-4">
                                <h4 className="text-sm font-medium text-purple-400 mb-2">
                                    Cluster {clusterId} ({(eventIds as string[]).length} events)
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {(eventIds as string[]).slice(0, 10).map((eventId) => (
                                        <span
                                            key={eventId}
                                            className="text-xs font-mono bg-white/5 px-2 py-1 rounded text-muted-foreground"
                                        >
                                            {eventId.slice(0, 8)}...
                                        </span>
                                    ))}
                                    {(eventIds as string[]).length > 10 && (
                                        <span className="text-xs text-muted-foreground">
                                            +{(eventIds as string[]).length - 10} more
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {clusters && clusters.cluster_count === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    No clusters detected. Try sending more events with varied content.
                </div>
            )}
        </div>
    );
}
