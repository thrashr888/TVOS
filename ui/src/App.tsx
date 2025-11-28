import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Activity,
  Search,
  TrendingUp,
  Network,
  LayoutDashboard,
  Clock,
  AlertTriangle,
  Terminal,
  Map,
} from 'lucide-react'
import { EventStream } from './components/EventStream'
import { SemanticSearch } from './components/SemanticSearch'
import { DriftChart } from './components/DriftChart'
import { ClusterView } from './components/ClusterView'
import { Dashboard } from './components/Dashboard'
import { AnomalyFeed } from './components/AnomalyFeed'
import { EmbeddingExplorer } from './components/EmbeddingExplorer'
import { TVQLConsole } from './components/TVQLConsole'
import './index.css'

const queryClient = new QueryClient()

type Tab =
  | 'dashboard'
  | 'stream'
  | 'search'
  | 'drift'
  | 'clusters'
  | 'anomalies'
  | 'explorer'
  | 'tvql'

// Time ranges in hours
const TIME_RANGES = [
  { label: 'Live', value: 0 },
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
]

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [globalSearchQuery, setGlobalSearchQuery] = useState('')
  const [timeRange, setTimeRange] = useState(0) // 0 = Live

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setActiveTab('search')
  }

  const tabs = [
    { id: 'dashboard' as Tab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'stream' as Tab, label: 'Event Stream', icon: Activity },
    { id: 'search' as Tab, label: 'Semantic Search', icon: Search },
    { id: 'drift' as Tab, label: 'Drift', icon: TrendingUp },
    { id: 'clusters' as Tab, label: 'Clusters', icon: Network },
    { id: 'anomalies' as Tab, label: 'Anomalies', icon: AlertTriangle },
    { id: 'explorer' as Tab, label: 'Explorer', icon: Map },
    { id: 'tvql' as Tab, label: 'TVQL', icon: Terminal },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900">
      {/* Header */}
      <header className="glass sticky top-0 z-50 border-b border-white/10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-8">
            <div
              className="flex flex-shrink-0 cursor-pointer items-center gap-3"
              onClick={() => setActiveTab('dashboard')}
            >
              <div className="glow flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-orange-500">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="bg-gradient-to-r from-blue-400 to-orange-400 bg-clip-text text-2xl font-bold text-transparent">
                  TVOS
                </h1>
                <p className="hidden text-xs text-muted-foreground sm:block">
                  Temporal Vector OLAP System
                </p>
              </div>
            </div>

            {/* Global Search */}
            <div className="max-w-xl flex-1">
              <form onSubmit={handleGlobalSearch} className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={globalSearchQuery}
                  onChange={(e) => setGlobalSearchQuery(e.target.value)}
                  placeholder="Search across events..."
                  className="glass w-full rounded-full bg-white/5 py-2 pl-10 pr-4 text-sm text-foreground transition-all placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
              </form>
            </div>

            {/* Time Picker */}
            <div className="glass flex items-center gap-2 rounded-lg bg-white/5 p-1">
              <Clock className="ml-2 h-4 w-4 text-muted-foreground" />
              {TIME_RANGES.map((range) => (
                <button
                  key={range.label}
                  onClick={() => setTimeRange(range.value)}
                  className={cn(
                    'rounded-md px-3 py-1 text-xs font-medium transition-all',
                    timeRange === range.value
                      ? 'bg-blue-500 text-white shadow-sm'
                      : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
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
      <nav className="glass sticky top-[73px] z-40 overflow-x-auto border-b border-white/10">
        <div className="container mx-auto px-6">
          <div className="flex min-w-max gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-6 py-4 text-sm font-medium transition-all',
                  '-mb-px border-b-2',
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                <tab.icon className="h-4 w-4" />
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
        {activeTab === 'anomalies' && <AnomalyFeed />}
        {activeTab === 'explorer' && <EmbeddingExplorer />}
        {activeTab === 'tvql' && <TVQLConsole />}
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
