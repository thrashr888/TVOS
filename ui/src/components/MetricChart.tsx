import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface MetricChartProps {
    title: string;
    metrics: string[];
    colors: string[];
    timeRangeHours?: number;
}

export function MetricChart({ title, metrics, colors, timeRangeHours = 1 }: MetricChartProps) {
    const { data: events, isLoading } = useQuery({
        queryKey: ['metrics', metrics.join(','), timeRangeHours],
        queryFn: async () => {
            const now = Date.now();
            const start = now - (timeRangeHours * 3600 * 1000);
            // Fetch more events to get good density
            const res = await fetch(`/api/query/window?start_ms=${start}&end_ms=${now}&limit=500`);
            const data = await res.json();
            return data.events || [];
        },
        refetchInterval: 30000,
    });

    if (isLoading) return <div className="h-64 flex items-center justify-center text-muted-foreground">Loading chart...</div>;

    // Transform data for Recharts
    // Filter events that have the requested metrics
    const chartData = events
        .filter((e: any) => e.metrics && metrics.some((m) => e.metrics[m] !== undefined))
        .map((e: any) => {
            const point: any = {
                time: new Date(e.timestamp_ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                timestamp: e.timestamp_ms,
            };
            metrics.forEach((m) => {
                if (e.metrics[m] !== undefined) {
                    point[m] = e.metrics[m];
                }
            });
            return point;
        })
        .sort((a: any, b: any) => a.timestamp - b.timestamp);

    if (chartData.length === 0) {
        return (
            <div className="glass rounded-lg p-6 h-full flex flex-col justify-center items-center">
                <h3 className="text-lg font-medium text-foreground mb-2">{title}</h3>
                <p className="text-muted-foreground text-sm">No data available for {metrics.join(', ')}</p>
            </div>
        );
    }

    return (
        <div className="glass rounded-lg p-6 h-full">
            <h3 className="text-lg font-medium text-foreground mb-4">{title}</h3>
            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis 
                            dataKey="time" 
                            stroke="rgba(255,255,255,0.5)" 
                            fontSize={12}
                            tickMargin={10}
                        />
                        <YAxis 
                            stroke="rgba(255,255,255,0.5)" 
                            fontSize={12}
                        />
                        <Tooltip 
                            contentStyle={{ backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)' }}
                            itemStyle={{ color: '#fff' }}
                        />
                        <Legend />
                        {metrics.map((metric, idx) => (
                            <Line
                                key={metric}
                                type="monotone"
                                dataKey={metric}
                                stroke={colors[idx % colors.length]}
                                strokeWidth={2}
                                dot={false}
                                activeDot={{ r: 4 }}
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

