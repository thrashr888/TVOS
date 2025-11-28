import zmq
import redis
import json
import time
from prometheus_client import start_http_server, Counter, Histogram
from tvos.config import Config
from tvos.db import get_db_connection
from tvos.protos.events_pb2 import EventPayload

# Metrics
EVENTS_INGESTED = Counter("tvos_ingest_events_total", "Total events ingested")
INGEST_LATENCY = Histogram(
    "tvos_ingest_latency_seconds", "Time spent processing an event"
)


def run_ingest_worker():
    # Setup ZeroMQ
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    receiver.bind(f"tcp://*:{Config.ZMQ_PULL_PORT}")

    # Setup Redis
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )

    # Setup DuckDB
    con = get_db_connection()

    print(f"Ingest worker started on port {Config.ZMQ_PULL_PORT}")

    while True:
        try:
            # Receive message
            msg = receiver.recv()
            start_time = time.time()

            # Deserialize
            event = EventPayload()
            event.ParseFromString(msg)

            # Insert into DuckDB
            con.execute(
                """
                INSERT INTO events (event_id, timestamp_ms, source, text_payload, metrics, metadata, embedding_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.timestamp_ms,
                    event.source,
                    event.text_payload,
                    json.dumps(dict(event.metrics)),
                    json.dumps(dict(event.metadata)),
                    None,  # embedding_id initially null
                ),
            )

            # Enqueue for embedding if text payload exists
            if event.text_payload:
                r.rpush("tvos:queue:embedding", event.event_id)

            # Publish to Redis for real-time UI
            r.publish(
                "events",
                json.dumps(
                    {
                        "event_id": event.event_id,
                        "timestamp_ms": event.timestamp_ms,
                        "source": event.source,
                        "text_payload": event.text_payload,
                        "metrics": dict(event.metrics),
                        "metadata": dict(event.metadata),
                    }
                ),
            )

            EVENTS_INGESTED.inc()
            INGEST_LATENCY.observe(time.time() - start_time)

        except Exception as e:
            print(f"Error processing event: {e}")
