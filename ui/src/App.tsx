import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Activity, Search, TrendingUp, Network, LayoutDashboard, Clock } from 'lucide-react';
import { EventStream } from './components/EventStream';
import { SemanticSearch } from './components/SemanticSearch';
import { DriftChart } from './components/DriftChart';
import { ClusterView } from './components/ClusterView';
import { Dashboard } from './components/Dashboard';
import './index.css';

const queryClient = new QueryClient();

type Tab = 'dashboard' | 'stream' | 'search' | 'drift' | 'clusters';

// Time ranges in hours
const TIME_RANGES = [
  { label: 'Live', value: 0 },
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
];

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState(0); // 0 = Live

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveTab('search');
  };

  const tabs = [
    { id: 'dashboard' as Tab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'stream' as Tab, label: 'Event Stream', icon: Activity },
    { id: 'search' as Tab, label: 'Semantic Search', icon: Search },
    { id: 'drift' as Tab, label: 'Drift Analysis', icon: TrendingUp },
    { id: 'clusters' as Tab, label: 'Clusters', icon: Network },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 glass sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-8">
            <div className="flex items-center gap-3 flex-shrink-0 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-orange-500 glow flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-orange-400 bg-clip-text text-transparent">
                  TVOS
                </h1>
                <p className="text-xs text-muted-foreground hidden sm:block">Temporal Vector OLAP System</p>
              </div>
            </div>

            {/* Global Search */}
            <div className="flex-1 max-w-xl">
              <form onSubmit={handleGlobalSearch} className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={globalSearchQuery}
                  onChange={(e) => setGlobalSearchQuery(e.target.value)}
                  placeholder="Search across events..."
                  className="w-full pl-10 pr-4 py-2 glass rounded-full bg-white/5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                />
              </form>
            </div>

            {/* Time Picker */}
            <div className="flex items-center gap-2 bg-white/5 rounded-lg p-1 glass">
              <Clock className="w-4 h-4 text-muted-foreground ml-2" />
              {TIME_RANGES.map((range) => (
                <button
                  key={range.label}
                  onClick={() => setTimeRange(range.value)}
                  className={cn(
                    'px-3 py-1 text-xs font-medium rounded-md transition-all',
                    timeRange === range.value
                      ? 'bg-blue-500 text-white shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                  )}
                >
                  {range.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-white/10 glass sticky top-[73px] z-40">
        <div className="container mx-auto px-6">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-6 py-4 text-sm font-medium transition-all',
                  'border-b-2 -mb-px',
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'stream' && <EventStream timeRange={timeRange} />}
        {activeTab === 'search' && <SemanticSearch externalQuery={globalSearchQuery} />}
        {activeTab === 'drift' && <DriftChart />}
        {activeTab === 'clusters' && <ClusterView />}
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
