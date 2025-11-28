from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import duckdb
import redis
import json
import threading
import asyncio
import time
from sentence_transformers import SentenceTransformer
from prometheus_client import make_asgi_app
from tvos.config import Config
from tvos.weaviate_client import WeaviateClient
from tvos.ingest import run_ingest_worker
from tvos.embed import run_embedding_worker
from tvos.analytics import run_analytics_worker

app = FastAPI(title="TVOS API")

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )
    p = r.pubsub()
    p.subscribe("events")

    try:
        while True:
            message = p.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        p.close()
        r.close()


# Start workers on startup
@app.on_event("startup")
def startup_event():
    # Start Ingest Worker
    t_ingest = threading.Thread(target=run_ingest_worker, daemon=True)
    t_ingest.start()
    print("Started Ingest Worker thread")

    # Start Embed Worker
    t_embed = threading.Thread(target=run_embedding_worker, daemon=True)
    t_embed.start()
    print("Started Embed Worker thread")

    # Start Analytics Worker
    t_analytics = threading.Thread(target=run_analytics_worker, daemon=True)
    t_analytics.start()
    print("Started Analytics Worker thread")


# Load model globally for now (or lazy load)
print("Loading model for API...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded.")


class SimilarityQuery(BaseModel):
    q: str
    limit: int = 10


class SearchResult(BaseModel):
    event_id: str
    score: float
    payload: Optional[dict] = None


@app.get("/stats")
def get_stats():
    from tvos.db import get_db_connection

    con = get_db_connection()
    count = con.execute("SELECT count(*) FROM events").fetchone()[0]
    # Do not close shared connection
    return {"event_count": count}


@app.post("/query/similarity", response_model=List[SearchResult])
def query_similarity(query: SimilarityQuery):
    # Generate vector
    vector = model.encode(query.q).tolist()

    # Query Weaviate
    wc = WeaviateClient()
    results = wc.search_similar(vector, limit=query.limit)
    wc.close()

    # Fetch details from DuckDB
    # We could do a join, but DuckDB is local file.
    # Let's just fetch by IDs.
    event_ids = [obj.properties["event_id"] for obj in results]

    if not event_ids:
        return []

    from tvos.db import get_db_connection

    con = get_db_connection()
    # Parameterized IN clause is tricky in python dbapi, let's construct manually safely since uuids
    placeholders = ",".join(["?"] * len(event_ids))
    rows = con.execute(
        f"SELECT event_id, text_payload, source, timestamp_ms FROM events WHERE event_id IN ({placeholders})",
        event_ids,
    ).fetchall()
    # Do not close shared connection

    # Map back to results
    row_map = {r[0]: {"text": r[1], "source": r[2], "ts": r[3]} for r in rows}

    output = []
    for obj in results:
        eid = obj.properties["event_id"]
        # Weaviate distance is 0..2 (cosine), we want similarity?
        # Weaviate returns 'distance' in metadata.
        # distance = 1 - cosine_similarity (roughly, depending on metric)
        # Let's just return distance for now or convert.
        dist = obj.metadata.distance

        if eid in row_map:
            output.append(SearchResult(event_id=eid, score=dist, payload=row_map[eid]))

    return output


@app.get("/query/window")
def query_window(start_ms: int, end_ms: int, limit: int = 100):
    """Query events in a time window"""
    # Use shared DuckDB connection

    try:
        from tvos.db import get_db_connection

        con = get_db_connection()
        rows = con.execute(
            "SELECT event_id, timestamp_ms, source, text_payload, metrics FROM events WHERE timestamp_ms >= ? AND timestamp_ms <= ? ORDER BY timestamp_ms DESC LIMIT ?",
            (start_ms, end_ms, limit),
        ).fetchall()
        # Do not close shared connection
    except Exception as e:
        print(f"Error querying DuckDB: {e}")
        return {"events": [], "count": 0, "error": str(e)}

    results = []
    for row in rows:
        results.append(
            {
                "event_id": row[0],
                "timestamp_ms": row[1],
                "source": row[2],
                "text_payload": row[3],
                "metrics": json.loads(row[4]) if row[4] else {},
            }
        )

    return {"events": results, "count": len(results)}


@app.get("/analytics/drift")
def get_drift():
    """Get semantic drift metrics from Redis"""
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )
    drift_data = r.get("tvos:hot:drift:1h")

    if not drift_data:
        raise HTTPException(status_code=404, detail="No drift data available")

    return json.loads(drift_data)


@app.get("/analytics/clusters")
def get_clusters():
    """Get cluster information from Redis"""
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )
    cluster_data = r.get("tvos:hot:clusters:24h")

    if not cluster_data:
        raise HTTPException(status_code=404, detail="No cluster data available")

    return json.loads(cluster_data)


@app.get("/analytics/stats")
def get_stats_window():
    """Get windowed statistics from Redis"""
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )
    stats_data = r.get("tvos:hot:stats:1h")

    if not stats_data:
        raise HTTPException(status_code=404, detail="No stats data available")

    return json.loads(stats_data)
