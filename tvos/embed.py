import redis
import json
import time
import uuid
from sentence_transformers import SentenceTransformer
from prometheus_client import start_http_server, Counter, Histogram
from tvos.config import Config
from tvos.db import get_db_connection
from tvos.weaviate_client import WeaviateClient

# Metrics
EMBEDDINGS_GENERATED = Counter(
    "tvos_embedding_jobs_total", "Total embeddings generated"
)
EMBEDDING_LATENCY = Histogram(
    "tvos_embedding_latency_seconds", "Time spent generating embedding"
)


def run_embedding_worker():
    # Setup Redis
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )

    # Setup Weaviate
    print("Connecting to Weaviate...")
    weaviate_client = WeaviateClient()
    weaviate_client.init_schema()
    print("Weaviate connected.")

    # Load Model
    print("Loading embedding model (this may take a minute)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded.")

    print("Embedding worker started")

    while True:
        try:
            # Blocking pop from queue
            # blpop returns tuple (key, value)
            item = r.blpop("tvos:queue:embedding", timeout=1)
            if not item:
                continue

            event_id = item[1]
            start_time = time.time()

            # Fetch event from DuckDB
            con = get_db_connection()
            # We need read-write connection to update later, but for now just read.
            # Actually, we should probably keep one connection open or open/close per job.
            # DuckDB concurrency: single process write, multiple read.
            # If ingest is writing, we might block.
            # Ideally, we'd use the same process or coordinate.
            # For this PoC, let's try to open, read, close.

            # Note: DuckDB doesn't support concurrent writers from different processes well in file mode.
            # This is a known limitation. For a real system, we might need a single writer service or use DuckDB in client-server mode (experimental) or just retry.
            # OR, we assume ingest is the only writer to 'events' and we only update 'embeddings' table?
            # But we need to update 'events.embedding_id'.
            # A common pattern with DuckDB is single-writer.
            # If Ingest is writing, Embed worker cannot write to the same file easily.
            # HACK: For this PoC, we might hit locks.
            # Alternative: Embed worker writes to a separate DuckDB file? No, we need joins.
            # Alternative: Embed worker sends "update" command back to Ingest?
            # Alternative: We use a mutex or just retry?
            # Let's try standard connect and see if it works (it might fail if Ingest has lock).
            # If it fails, we might need to rethink the "Distributed Workers" with "Local DuckDB" aspect.
            # Actually, for a "Local-First" system, usually it's one process.
            # But the RFC says "Ingest Worker", "Embedding Worker".
            # Maybe they should be threads in the same process?
            # Or we use DuckDB's experimental concurrent write?
            # Let's try to implement as separate process but handle locks or just use one process with threads if needed.
            # For now, let's implement and see.

            row = con.execute(
                "SELECT text_payload, timestamp_ms, source FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if not row:
                print(f"Event {event_id} not found")
                # Do not close shared connection
                continue

            text_payload, timestamp_ms, source = row

            # Generate Embedding
            vector = model.encode(text_payload).tolist()

            # Store in Weaviate
            weaviate_client.insert_embedding(event_id, vector, timestamp_ms, source)

            # Store Metadata in DuckDB
            embedding_id = str(uuid.uuid4())
            # Update event with embedding_id
            # This is the danger zone for locks.
            con.execute(
                "UPDATE events SET embedding_id = ? WHERE event_id = ?",
                (embedding_id, event_id),
            )
            con.execute(
                "INSERT INTO embeddings (embedding_id, vector_dim, created_at) VALUES (?, ?, current_timestamp)",
                (embedding_id, len(vector)),
            )

            # Do not close shared connection

            EMBEDDINGS_GENERATED.inc()
            EMBEDDING_LATENCY.observe(time.time() - start_time)
            print(f"Processed embedding for {event_id}")

        except Exception as e:
            print(f"Error processing embedding: {e}")
            # If we failed, maybe push back to queue?
            # r.rpush("tvos:queue:embedding", event_id)
            time.sleep(1)
