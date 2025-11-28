# TVOS - Temporal Vector OLAP System

A local-first analytical engine combining DuckDB, Weaviate, Redis, and ZeroMQ for temporal semantic analytics.

## 🚀 Quick Start (Docker)

The easiest way to run TVOS is with Docker:

```bash
# Start everything
docker compose up -d

# Initialize Weaviate schema (one time)
docker compose exec api python tvos/weaviate_client.py

# Send test events
docker compose exec ingest python scripts/produce_test_event.py
```

Visit **http://localhost:3000** to see the UI!

### Services

Once running, you'll have:
- **UI**: http://localhost:3000
- **API**: http://localhost:8003
- **API Docs**: http://localhost:8003/docs
- **Prometheus**: http://localhost:19090
- **Weaviate**: http://localhost:8080

### View Logs

```bash
docker compose logs -f          # All services
docker compose logs -f api      # Just API
docker compose logs -f ui       # Just UI
```

### Stop Everything

```bash
docker compose down             # Stop services
docker compose down -v          # Stop and remove volumes (fresh start)
```

## 🎯 What is TVOS?

TVOS provides **temporal vector analytics** - the ability to:
- Store events with both tabular (SQL) and vector (semantic) representations
- Run SQL queries while also performing semantic similarity searches
- Compare semantic meaning across time windows
- Detect semantic drift and cluster similar events over time

Traditional time-series systems focus on numeric metrics. Vector databases focus on semantic search. **TVOS combines both with time.**

## 🏗️ Architecture

```
Producer → ZeroMQ → Ingest Worker → DuckDB
                         ↓
                    Redis Queue
                         ↓
                  Embedding Worker → Weaviate
                         ↓
                    DuckDB (update)
                         ↓
                  Analytics Worker → Redis (hot windows)
                         
API + UI ← DuckDB + Weaviate + Redis
```

## 📊 Features

### Event Ingestion
- **ZeroMQ** PUSH/PULL pattern for distributed ingestion
- **Protobuf** for type-safe event serialization
- **DuckDB** for columnar OLAP storage

### Semantic Embeddings
- Local embedding generation with **sentence-transformers**
- Vector storage in **Weaviate**
- Automatic embedding pipeline via Redis queues

### Temporal Analytics
- **Windowed queries** - SQL over time ranges
- **Semantic drift detection** - Compare embedding centroids across windows
- **Vector clustering** - HDBSCAN clustering over time
- **Redis hot windows** - Fast access to recent analytics

### Modern UI
- **React + TypeScript + Vite**
- **Tailwind CSS** with dark mode and glassmorphism
- **Real-time updates** - Auto-refreshing event stream
- **Interactive visualizations** - Drift charts and cluster views

## 🔌 API Endpoints

### Query
- `GET /stats` - System statistics
- `GET /query/window?start_ms=&end_ms=&limit=` - Query events by time range
- `POST /query/similarity` - Semantic search

### Analytics
- `GET /analytics/drift` - Semantic drift metrics
- `GET /analytics/clusters` - HDBSCAN cluster results
- `GET /analytics/stats` - Windowed statistics

### Example

```bash
# Semantic search
curl -X POST http://localhost:8003/query/similarity \
  -H "Content-Type: application/json" \
  -d '{"q": "test message", "limit": 5}'

# Get drift metrics
curl http://localhost:8003/analytics/drift

# Windowed query
START=$(date -u -v-1H +%s)000
END=$(date -u +%s)000
curl "http://localhost:8003/query/window?start_ms=$START&end_ms=$END"
```

## 🛠️ Development Setup (Without Docker)

If you want to run services individually for development:

### 1. Start Infrastructure

```bash
docker compose up -d weaviate redis prometheus
```

### 2. Install Python Dependencies

```bash
uv sync
```

### 3. Initialize Weaviate Schema

```bash
uv run python tvos/weaviate_client.py
```

### 4. Run Workers (in separate terminals)

```bash
uv run python tvos/ingest.py      # Terminal 1 (port 8000)
uv run python tvos/embed.py       # Terminal 2 (port 8001)
uv run python tvos/analytics.py   # Terminal 3 (port 8002)
uv run uvicorn tvos.api:app --reload  # Terminal 4 (port 8000)
```

### 5. Run UI

```bash
cd ui
npm install
npm run dev  # http://localhost:5173
```

### 6. Send Test Events

```bash
uv run python scripts/produce_test_event.py
```

## 📈 Metrics

- Ingest: http://localhost:8000/metrics
- Embedding: http://localhost:8001/metrics
- Analytics: http://localhost:8002/metrics
- Prometheus: http://localhost:19090

## 🏛️ Components

### Core Workers
- `tvos/ingest.py` - ZeroMQ PULL worker, stores events in DuckDB
- `tvos/embed.py` - Generates embeddings, stores in Weaviate
- `tvos/analytics.py` - Computes drift, clusters, windowed stats

### Data Layer
- `tvos/db.py` - DuckDB schema and connection
- `tvos/weaviate_client.py` - Weaviate wrapper

### API & Config
- `tvos/api.py` - FastAPI server
- `tvos/config.py` - Configuration management

### Protocol
- `protos/events.proto` - Protobuf event schema

## 🛣️ Roadmap

- ✅ Phase 1: Core Plumbing
- ✅ Phase 2: Embeddings + Analytics
- ✅ Phase 3: Temporal OLAP
- ✅ Phase 4: UI Development
- 🔨 Phase 5: Hardening (Future)

## 📝 License

This is a proof-of-concept implementation following RFC-001.

## 🙏 Acknowledgments

Built with:
- [DuckDB](https://duckdb.org/) - Fast analytical queries
- [Weaviate](https://weaviate.io/) - Vector database
- [ZeroMQ](https://zeromq.org/) - Distributed messaging
- [sentence-transformers](https://www.sbert.net/) - Semantic embeddings
- [FastAPI](https://fastapi.tiangolo.com/) - Modern API framework
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) - UI framework
