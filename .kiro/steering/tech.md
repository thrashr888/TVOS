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

## AI-Assisted Workflow
- **Kiro Hooks**: Automated code review triggers
  - `ui-design-review.kiro.hook`: Reviews UI changes for design system consistency, accessibility, and performance
  - `backend-review.kiro.hook`: Reviews Python code for architecture, type safety, and async correctness

## DuckDB Best Practices

### Connection Management
- **Use the shared connection**: Always use `get_db_connection()` from `tvos.db`
- **Never create new connections**: DuckDB uses file-based locking; multiple connections can cause conflicts
- **Thread-safe**: The shared connection is thread-safe and protected by a lock
- **Don't close the connection**: The shared connection persists for the application lifetime

### Database Initialization
- **Use `init_db()`**: Call once at application startup to create tables and indexes
- **Idempotent schema**: All `CREATE TABLE` statements use `IF NOT EXISTS`
- **Reset for testing**: Set `tvos.db._SHARED_CONN = None` to reset the global connection in tests

### Testing with DuckDB
```python
# Create a temporary test database
import tempfile
import os

def setup_test_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.duckdb')
    
    # Override config
    Config.DUCKDB_PATH = db_path
    
    # Reset global connection
    import tvos.db
    tvos.db._SHARED_CONN = None
    
    # Initialize schema
    from tvos.db import init_db
    init_db()
    
    return db_path

# Clean up after tests
def cleanup_test_db(db_path):
    import shutil
    shutil.rmtree(os.path.dirname(db_path))
```

### Common Patterns
```python
# Get connection
from tvos.db import get_db_connection
conn = get_db_connection()

# Execute query
result = conn.execute("SELECT * FROM events WHERE source = ?", [source]).fetchall()

# Insert with parameters (prevents SQL injection)
conn.execute(
    "INSERT INTO events (event_id, timestamp_ms, source) VALUES (?, ?, ?)",
    [event_id, timestamp, source]
)

# Check if record exists
exists = conn.execute(
    "SELECT COUNT(*) FROM events WHERE event_id = ?", 
    [event_id]
).fetchone()[0] > 0
```

### Avoid Common Pitfalls
- **Don't use string formatting for SQL**: Always use parameterized queries with `?` placeholders
- **Don't create temporary files with content**: Let DuckDB create the database file itself
- **Don't mix read-only and read-write modes**: Always use read-write mode (default)
- **Don't forget to handle NULL values**: Use `COALESCE()` or check for None in Python

## Code Style
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode enabled
- **Formatting**: Prettier for frontend, Black/Ruff for Python
- **Linting**: ESLint for frontend, Ruff for Python