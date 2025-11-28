# TVOS Project Structure

## Root Directory Layout

```
├── tvos/                    # Main Python package
├── ui/                      # React frontend application
├── scripts/                 # Utility and development scripts
├── protos/                  # Protocol Buffer definitions
├── .kiro/                   # Kiro IDE configuration
├── docker-compose.yml       # Multi-service orchestration
├── pyproject.toml          # Python project configuration
└── README.md               # Project documentation
```

## Core Python Package (`tvos/`)

```
tvos/
├── __init__.py
├── api.py                  # FastAPI server with all endpoints
├── config.py               # Environment configuration
├── db.py                   # DuckDB schema and connections
├── ingest.py               # ZeroMQ event ingestion worker
├── embed.py                # Embedding generation worker
├── analytics.py            # Drift detection and clustering
├── weaviate_client.py      # Weaviate vector database client
├── llm.py                  # LLM integration for chat features
├── tvql.py                 # Custom query language parser
└── protos/                 # Generated Protocol Buffer code
    ├── __init__.py
    ├── events_pb2.py       # Generated from protos/events.proto
    └── events_pb2.pyi      # Type stubs
```

## Frontend Application (`ui/`)

```
ui/
├── src/
│   ├── components/         # React components
│   │   ├── Dashboard.tsx   # Main dashboard layout
│   │   ├── EventStream.tsx # Real-time event feed
│   │   ├── ChatInterface.tsx # LLM chat interface
│   │   ├── SemanticSearch.tsx # Vector search UI
│   │   ├── DriftChart.tsx  # Semantic drift visualization
│   │   ├── ClusterView.tsx # Clustering visualization
│   │   ├── EmbeddingExplorer.tsx # 2D embedding projection
│   │   ├── TVQLConsole.tsx # Query interface
│   │   ├── MetricChart.tsx # Time-series charts
│   │   └── AnomalyFeed.tsx # Anomaly detection display
│   ├── lib/
│   │   ├── api.ts          # API client functions
│   │   └── utils.ts        # Utility functions
│   ├── App.tsx             # Main application component
│   └── main.tsx            # Application entry point
├── package.json            # Node.js dependencies
├── vite.config.ts          # Vite build configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

## Development Scripts (`scripts/`)

```
scripts/
├── compile_protos.sh       # Generate Python code from .proto files
├── run_collectors.sh       # Start all data collectors
├── produce_test_event.py   # Send test events for development
├── check_db.py             # Verify DuckDB schema and data
├── check_embeddings.py     # Verify Weaviate embeddings
├── run_analytics.py        # Manual analytics computation
├── ingest_shell_history.py # Collect shell command history
├── ingest_browser_history.py # Collect browser history
├── ingest_system_metrics.py # Collect system performance data
└── verify_*.py             # Various verification scripts
```

## Architecture Patterns

### Worker Pattern
- Each core function runs as a separate worker thread
- Workers communicate via Redis queues and shared DuckDB
- All workers run within the single API process for DuckDB concurrency

### Data Flow
1. **Events** → ZeroMQ → **Ingest Worker** → DuckDB
2. **Ingest Worker** → Redis Queue → **Embedding Worker** → Weaviate
3. **Analytics Worker** → Periodic computation → Redis (hot windows)
4. **API** → Query DuckDB/Weaviate/Redis → **UI**

### Configuration
- Environment variables in `.env` file
- Docker Compose for service orchestration
- Shared configuration in `tvos/config.py`

### Database Schema
- **DuckDB**: Events table with metadata and embedding references
- **Weaviate**: Vector embeddings with event metadata
- **Redis**: Queues, locks, and hot analytical results

### API Design
- RESTful endpoints for queries and analytics
- WebSocket for real-time event streaming
- Prometheus metrics at `/metrics`
- Auto-generated docs at `/docs`