# TVOS Product Overview

TVOS (Temporal Vector OLAP System) is a local-first analytical engine that combines temporal analytics with semantic search capabilities.

## Core Purpose
- Store events with both tabular (SQL) and vector (semantic) representations
- Enable temporal semantic analytics - comparing meaning across time windows
- Detect semantic drift and cluster similar events over time
- Provide unified querying across structured data and embeddings

## Key Capabilities
- **Event Ingestion**: ZeroMQ-based distributed event collection with Protobuf serialization
- **Semantic Embeddings**: Automatic embedding generation and vector storage in Weaviate
- **Temporal OLAP**: DuckDB for columnar analytics with time-series capabilities
- **Real-time Analytics**: Drift detection, clustering, and windowed statistics
- **Modern UI**: React-based dashboard with real-time visualizations

## Architecture Philosophy
- Local-first and offline-capable
- Designed for research loops, agent systems, and product telemetry investigation
- Migration path from Python to Go for performance-critical components
- Unified storage of both structured and semantic data