RFC-001: Temporal Vector OLAP System (TVOS)

Status: Draft
Authors: Paul Thrasher
Created: 2025-11-27
Target Language (v0): Python
Upgrade Path: Go for ingestion/metrics later
Version: 0.1

⸻

1. Overview

Temporal Vector OLAP System (TVOS) is a local-first analytical engine that combines:
• DuckDB – columnar OLAP for time-series + event analytics
• Weaviate – vector embeddings + semantic similarity search
• Redis – hot time windows, locks, coordination, ephemeral results
• ZeroMQ – distributed event ingestion + fan-out
• Protobuf – typed event schema (stable contracts for rewrite in Go later)
• Prometheus – metrics + observability

The goal is to create a temporal semantic analytics system capable of:
• ingesting structured/unstructured events,
• embedding the semantic payload,
• storing both tabular and vector representations,
• and enabling rich temporal analysis (semantic drift, clustering, windowed OLAP).

This is intentionally offline-capable, low-latency, and portable—targeted at advanced research loops, agent systems, or product telemetry investigation.

⸻

2. Problem Statement

Traditional time-series systems (Prometheus, InfluxDB, Timescale) focus on numeric metrics, not semantics.
Vector databases focus on semantic search, not time.

TVOS provides temporal vector analytics:
• store events and embeddings together,
• run SQL over time while also running semantic similarity queries,
• compare semantic meaning across time windows,
• perform anomaly detection in embedding space,
• build drift detection pipelines.

No existing open-source tool provides this in a unified local-first engine.

⸻

3. Core Capabilities
   1. Event Ingestion
      • ZeroMQ PUSH → PULL workers.
      • Events serialized via Protobuf.
      • Producers can be Python or Go.
   2. Semantic Embedding
      • Each event’s payload is embedded via local LLM or remote provider.
      • Embeddings stored in Weaviate.
      • Embedding metadata stored in DuckDB.
   3. Temporal OLAP
      • DuckDB stores:
      • event_id
      • timestamp
      • source
      • numeric features
      • metadata
      • embedding_id
      • Analytics:
      • sliding window aggregates
      • grouping by time buckets
      • clustering (KMeans / HDBSCAN) over windows
      • semantic drift metrics (vector deltas)
   4. Hot Windows (Redis)
      • hot data (last N minutes/hours)
      • ephemeral aggregates
      • job queues (embedding, anomaly detection)
   5. Observability (Prometheus)
      • ingestion rate
      • embedding latency
      • ZeroMQ queue depth
      • Weaviate QPS
      • DuckDB query time
   6. APIs (FastAPI)
      • ingest event (optional direct ingest for tests)
      • query by time window
      • semantic search API
      • combined temporal+semantic query (“search similar events in last N hours”)

⸻

4. Proposed Architecture

4.1 Components 1. Ingest Worker (tvos_ingest_worker)
• PULL socket from ZeroMQ
• Deserialize Protobuf
• Normalize event
• Store raw event into DuckDB
• Enqueue embedding job into Redis 2. Embedding Worker (tvos_embed_worker)
• Pop jobs from Redis queue
• Compute embedding
• Store vector in Weaviate
• Update DuckDB with embedding reference 3. Analytics Worker (tvos_analytics_worker)
• Periodic window computations
• Compute drift, similarity windows, clusters
• Write results into Redis (hot)
• Export metrics to Prometheus 4. API Server (tvos_api)
• FastAPI or bare ASGI
• Endpoints:
• /query/window?start=&end=
• /query/similarity?q=&window=1h
• /stats
• /metrics (Prometheus) 5. ZeroMQ Producer(s)
• Simple library for publishing events.

⸻

5. Data Model

5.1 Protobuf (events.proto)

syntax = "proto3";

message EventPayload {
string event_id = 1;
int64 timestamp_ms = 2;
string source = 3;
string text_payload = 4; // optional
map<string, double> metrics = 5;
map<string, string> metadata = 6;
}

5.2 DuckDB Tables

events

column type notes
event_id VARCHAR PK
timestamp_ms BIGINT index
source VARCHAR
text_payload VARCHAR
metrics JSON
metadata JSON
embedding_id VARCHAR FK

embeddings

column type notes
embedding_id VARCHAR PK
vector_dim INTEGER
created_at TIMESTAMP

⸻

6. ZeroMQ Patterns
   • Producers → Ingest Worker
   • Pattern: PUSH → PULL
   • Rationale: fan-out without backpressure complexity.
   • Optional Future: ROUTER/DEALER for more dynamic routing.

⸻

7. Redis Usage
   • tvos:queue:embedding → list of events needing embeddings
   • tvos:hot:<window> → last N minutes of materialized features
   • locks: for analytics jobs

⸻

8. Weaviate Schema

{
"classes": [
{
"class": "EventEmbedding",
"vectorizer": "no-vectorizer",
"properties": [
{ "name": "event_id", "dataType": ["string"] },
{ "name": "timestamp", "dataType": ["date"] },
{ "name": "source", "dataType": ["string"] }
]
}
]
}

Embeddings are provided manually (no internal vectorizer).

⸻

9. Prometheus Metrics

Expose via /metrics:
• tvos_ingest_events_total
• tvos_ingest_latency_seconds
• tvos_embedding_jobs_total
• tvos_embedding_latency_seconds
• tvos_weaviate_request_duration_seconds
• tvos_duckdb_query_seconds
• tvos_semantic_drift_score

⸻

10. Security / Assumptions
    • Local-first system on trusted host.
    • Authentication optional for PoC.

⸻

11. Testing Strategy
    1.  Unit tests
        • Protobuf serialization
        • DuckDB schema correctness
        • Redis queue ops
        • Weaviate insert/query
    2.  Integration tests
        • ZeroMQ → ingest → embedding → Weaviate → DuckDB flow
    3.  Load testing
        • measure event ingestion throughput
        • measure embedding latency

⸻

12. Migration Path to Go

The reason we use Protobuf + ZeroMQ from the start:
• Ingest Worker can be rewritten in Go later:
• same message schema
• same ZeroMQ pattern
• same Redis queues

Nothing in the architecture binds you to Python permanently.

⸻

13. Implementation Roadmap

Phase 1 — Core Plumbing
• Repo scaffolding
• Protobuf schema + Python build pipeline
• ZeroMQ ingest worker
• DuckDB event table
• Prometheus basic metrics

Phase 2 — Embeddings + Analytics
• Embedding worker
• Weaviate integration
• DuckDB embedding reference updates
• Basic semantic search API

Phase 3 — Temporal OLAP
• Windowed queries in DuckDB
• Drift metrics
• Vector clustering over time
• Redis hot windows

Phase 4 — UI Development
• Dashboard layout and navigation
• Real-time event stream view
• Semantic search interface
• Analytics visualizations (drift, clusters)
• Time window controls

Phase 5 — Hardening
• Go rewrite of ingestion path
• Full Prometheus dashboards
• Frontend (optional)
• Documentation
• Testing
• CI/CD

⸻

14. UI Strategy

14.1 Framework Choice
• React (Vite + TypeScript) chosen for the rich ecosystem of data visualization libraries (Recharts, Visx) and high-quality component systems (ShadcnUI).
• Tailwind CSS for styling to ensure a modern, world-class aesthetic.
• State Management: TanStack Query (server state) + Zustand (client state).

14.2 Communication Layer
• Hybrid approach:
• REST (FastAPI): For stateless request/response interactions (historical queries, search, configuration). Easier to cache, debug, and document.
• WebSockets: Strictly for real-time feeds (event streaming, live drift metrics, system health).
• gRPC-Web considered but rejected for initial simplicity; JSON over HTTP/WS is sufficient for the UI.

14.3 Core Views
• Live Stream: WebSocket-fed list of incoming events with semantic highlighting.
• OLAP Explorer: Time-series charts (line/bar) showing aggregation over windows.
• Semantic Map: Interactive scatter plot visualizing vector embeddings (reduced via UMAP/PCA) to show clusters and drift.

⸻

15. Future Extensions (Optional)
    • Multimodal event embeddings (images/audio)
    • On-device embedding models (GGUF)
    • Streaming UMAP for real-time semantic drift visualization
    • HTMX dashboard (fits your style)
    • Rookery agent workers that self-analyze the OLAP outputs

⸻

We should also generate:
• A full repo structure, ready-cloneable
• docker-compose for Weaviate + Redis + Prometheus
• scaffolded Python packages for each worker
• ZeroMQ producer example
• An architecture diagram in Mermaid
