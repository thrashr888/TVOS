import redis
import json
import time
import traceback
import numpy as np
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import hdbscan
from prometheus_client import start_http_server, Counter, Gauge
from tvos.config import Config
from tvos.db import get_db_connection
from tvos.weaviate_client import WeaviateClient

# Metrics
ANALYTICS_RUNS = Counter("tvos_analytics_runs_total", "Total analytics runs")
DRIFT_SCORE = Gauge("tvos_semantic_drift_score", "Current semantic drift score")
CLUSTER_COUNT = Gauge("tvos_cluster_count", "Number of clusters detected")


def compute_windowed_stats(window_hours=1):
    """Compute statistics for a time window"""
    con = get_db_connection()

    # Get current time and window start
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - (window_hours * 3600 * 1000)

    # Count events in window
    count = con.execute(
        "SELECT count(*) FROM events WHERE timestamp_ms >= ?", (window_start_ms,)
    ).fetchone()[0]

    # Avg metrics
    metrics_data = con.execute(
        "SELECT metrics FROM events WHERE timestamp_ms >= ? AND metrics IS NOT NULL",
        (window_start_ms,),
    ).fetchall()

    avg_metrics = {}
    if metrics_data:
        all_metrics = defaultdict(list)
        for (metrics_json,) in metrics_data:
            metrics = json.loads(metrics_json)
            for key, value in metrics.items():
                all_metrics[key].append(value)

        avg_metrics = {k: np.mean(v) for k, v in all_metrics.items()}

    # Do not close shared connection

    return {
        "window_hours": window_hours,
        "event_count": count,
        "avg_metrics": avg_metrics,
        "timestamp": now_ms,
    }


import weaviate.classes.config as wvc
import weaviate.classes.query as wvq


def compute_semantic_drift(window_hours=1):
    """Compute semantic drift between consecutive time windows"""
    wc = WeaviateClient()
    print(f"DEBUG: WeaviateClient: {wc}, client: {getattr(wc, 'client', 'No client')}")
    if hasattr(wc.client, "collections"):
        print("DEBUG: client has collections")
    else:
        print(f"DEBUG: client attributes: {dir(wc.client)}")

    # Get current time
    now = datetime.now(timezone.utc)

    # Define two consecutive windows
    window1_start = now - timedelta(hours=window_hours * 2)
    window1_end = now - timedelta(hours=window_hours)
    window2_start = window1_end
    window2_end = now

    # Fetch vectors for each window
    collection = wc.client.collections.get("EventEmbedding")

    # Window 1
    response1 = collection.query.fetch_objects(
        filters=wvq.Filter.by_property("timestamp").greater_or_equal(window1_start)
        & wvq.Filter.by_property("timestamp").less_than(window1_end),
        limit=1000,
        include_vector=True,
    )

    # Window 2
    response2 = collection.query.fetch_objects(
        filters=wvq.Filter.by_property("timestamp").greater_or_equal(window2_start)
        & wvq.Filter.by_property("timestamp").less_than(window2_end),
        limit=1000,
        include_vector=True,
    )

    # Do not close Weaviate client as it might be reused or is lightweight?
    # Actually, WeaviateClient creates a new connection in __init__.
    # If we run this in a loop, we should probably keep one client instance or close it properly.
    # The WeaviateClient wrapper uses connect_to_local.
    wc.close()

    if not response1.objects or not response2.objects:
        return {"drift_score": 0.0, "reason": "insufficient_data"}

    # Compute centroids
    vectors1 = np.array([obj.vector for obj in response1.objects])
    vectors2 = np.array([obj.vector for obj in response2.objects])

    centroid1 = np.mean(vectors1, axis=0)
    centroid2 = np.mean(vectors2, axis=0)

    # Cosine distance
    from sklearn.metrics.pairwise import cosine_similarity

    similarity = cosine_similarity([centroid1], [centroid2])[0][0]
    drift_score = 1 - similarity  # Convert to distance

    return {
        "drift_score": float(drift_score),
        "window1_count": len(response1.objects),
        "window2_count": len(response2.objects),
        "window_hours": window_hours,
    }


def compute_clusters(window_hours=24, min_cluster_size=2):
    """Cluster embeddings in a time window using HDBSCAN"""
    wc = WeaviateClient()

    # Get vectors from last N hours
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    collection = wc.client.collections.get("EventEmbedding")
    response = collection.query.fetch_objects(
        filters=wvq.Filter.by_property("timestamp").greater_or_equal(window_start),
        limit=1000,
        include_vector=True,
    )

    wc.close()

    if len(response.objects) < min_cluster_size:
        return {"cluster_count": 0, "reason": "insufficient_data"}

    # Extract vectors and event IDs
    vectors = np.array([obj.vector for obj in response.objects])
    event_ids = [obj.properties["event_id"] for obj in response.objects]

    # Cluster with HDBSCAN
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="cosine")
    labels = clusterer.fit_predict(vectors)

    # Count clusters (excluding noise, label=-1)
    unique_labels = set(labels)
    cluster_count = len([l for l in unique_labels if l != -1])

    # Group events by cluster
    clusters = defaultdict(list)
    for event_id, label in zip(event_ids, labels):
        clusters[int(label)].append(event_id)

    return {
        "cluster_count": cluster_count,
        "total_events": len(event_ids),
        "noise_count": list(labels).count(-1),
        "clusters": {k: v for k, v in clusters.items() if k != -1},
    }


def run_analytics_worker(interval_seconds=60):
    """Run analytics periodically"""
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )

    print("Analytics worker started")

    while True:
        try:
            print(f"Running analytics at {datetime.now()}")

            # Compute windowed stats
            stats = compute_windowed_stats(window_hours=1)
            r.set("tvos:hot:stats:1h", json.dumps(stats), ex=3600)
            print(f"  Stats: {stats['event_count']} events in last hour")

            # Compute drift
            drift = compute_semantic_drift(window_hours=1)
            r.set("tvos:hot:drift:1h", json.dumps(drift), ex=3600)
            DRIFT_SCORE.set(drift.get("drift_score", 0.0))
            print(f"  Drift: {drift.get('drift_score', 0.0):.4f}")

            # Compute clusters
            clusters = compute_clusters(window_hours=24, min_cluster_size=2)
            r.set("tvos:hot:clusters:24h", json.dumps(clusters), ex=86400)
            CLUSTER_COUNT.set(clusters.get("cluster_count", 0))
            print(f"  Clusters: {clusters.get('cluster_count', 0)}")

            ANALYTICS_RUNS.inc()

        except Exception as e:
            print(f"Error in analytics: {e}")
            traceback.print_exc()

        time.sleep(interval_seconds)
