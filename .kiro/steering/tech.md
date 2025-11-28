# TVOS Technology Stack

## Core Technologies

### Backend (Python)
- **FastAPI**: REST API server with automatic OpenAPI docs
- **DuckDB**: Columnar OLAP database for event storage and analytics
- **Weaviate**: Vector database for semantic embeddings
- **Redis**: Message queues, hot windows, and coordination
- **ZeroMQ**: Distributed messaging for event ingestion
- **Protobuf**: Type-safe event serialization

### Machine Learning
- **sentence-transformers**: Local embedding generation (all-MiniLM-L6-v2)
- **scikit-learn**: Clustering and analytics
- **HDBSCAN**: Density-based clustering
- **UMAP**: Dimensionality reduction for visualizations

### Frontend (TypeScript/React)
- **React 19** with TypeScript
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **TanStack Query**: Server state management
- **Zustand**: Client state management
- **Recharts**: Data visualization
- **Lucide React**: Icon library

### Infrastructure
- **Docker Compose**: Multi-service orchestration
- **Prometheus**: Metrics collection and monitoring
- **uv**: Python package management
- **nginx**: Production web server (UI)

## Build System

### Python Environment
```bash
# Install dependencies
uv sync

# Compile Protocol Buffers
./scripts/compile_protos.sh

# Run development server
uv run uvicorn tvos.api:app --reload
```

### Frontend Development
```bash
cd ui
npm install
npm run dev          # Development server (port 5173)
npm run build        # Production build
npm run lint         # ESLint
npm run format       # Prettier
```

### Docker Operations
```bash
# Start all services
docker compose up -d

# Initialize Weaviate schema (one-time)
docker compose exec api python tvos/weaviate_client.py

# View logs
docker compose logs -f api
docker compose logs -f ui

# Fresh restart
docker compose down -v && docker compose up -d
```

### Testing & Scripts
```bash
# Send test events
uv run python scripts/produce_test_event.py

# Check database
uv run python scripts/check_db.py

# Verify embeddings
uv run python scripts/check_embeddings.py

# Run analytics
uv run python scripts/run_analytics.py
```

## Development Ports
- **API**: 8000 (FastAPI with auto-docs at /docs)
- **UI**: 3000 (production) / 5173 (development)
- **Weaviate**: 8080
- **Redis**: 6379
- **Prometheus**: 19090
- **ZeroMQ**: 5555 (PULL socket)

## Code Style
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode enabled
- **Formatting**: Prettier for frontend, Black/Ruff for Python
- **Linting**: ESLint for frontend, Ruff for Python