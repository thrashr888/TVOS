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
from tvos.llm import LLMClient
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA

try:
    import umap
except ImportError:
    umap = None
import uuid

# Metrics
# Metrics
ANALYTICS_RUNS = Counter("tvos_analytics_runs_total", "Total analytics runs")
DRIFT_SCORE = Gauge("tvos_semantic_drift_score", "Current semantic drift score")
CLUSTER_COUNT = Gauge("tvos_cluster_count", "Number of clusters detected")
ANOMALY_COUNT = Gauge("tvos_anomaly_count", "Number of anomalies detected")


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
    try:
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
    except Exception as e:
        print(f"Weaviate error in compute_semantic_drift: {e}")
        wc.close()
        return {"drift_score": 0.0, "reason": "error", "detail": str(e)}

    # Do not close Weaviate client as it might be reused or is lightweight?
    # Actually, WeaviateClient creates a new connection in __init__.
    # If we run this in a loop, we should probably keep one client instance or close it properly.
    # The WeaviateClient wrapper uses connect_to_local.
    wc.close()

    if not response1.objects or not response2.objects:
        return {"drift_score": 0.0, "reason": "insufficient_data"}

    # Compute centroids
    vectors1 = np.array([obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response1.objects])
    vectors2 = np.array([obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response2.objects])

    centroid1 = np.mean(vectors1, axis=0)
    centroid2 = np.mean(vectors2, axis=0)

    # Cosine distance
    from sklearn.metrics.pairwise import cosine_similarity

    similarity = cosine_similarity([centroid1], [centroid2])[0][0]
    drift_score = 1 - similarity  # Convert to distance

    drift_score_val = float(drift_score)

    # Persist drift history
    try:
        con = get_db_connection()
        con.execute(
            "INSERT INTO drift_history (timestamp_ms, score, window_hours) VALUES (?, ?, ?)",
            (int(now.timestamp() * 1000), drift_score_val, window_hours),
        )
    except Exception as e:
        print(f"Error persisting drift history: {e}")

    return {
        "drift_score": drift_score_val,
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
    vectors = np.array([obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response.objects])
    event_ids = [obj.properties["event_id"] for obj in response.objects]

    # Cluster with HDBSCAN
    # Note: Sklearn BallTree does not support cosine metric efficiently in some versions.
    # We use euclidean on normalized vectors if possible, or let hdbscan choose.
    # For now, switching to euclidean as standard vectors should be normalized or close enough for rough clustering.
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(vectors)

    # Count clusters (excluding noise, label=-1)
    unique_labels = set(labels)
    cluster_count = len([l for l in unique_labels if l != -1])

    # Group events by cluster
    clusters = defaultdict(list)
    for event_id, label in zip(event_ids, labels):
        clusters[int(label)].append(event_id)

    # Summarize clusters with LLM
    llm = LLMClient()
    summarized_clusters = {}

    for label, ids in clusters.items():
        if label == -1:
            continue

        # Get text payload for events in cluster
        # We need to fetch from DuckDB or Weaviate. Weaviate objects have properties?
        # The response object has properties.
        cluster_events = [
            obj.properties
            for obj in response.objects
            if obj.properties["event_id"] in ids
        ]

        # Find centroid of this cluster
        cluster_vectors = [
            obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response.objects if obj.properties["event_id"] in ids
        ]
        if not cluster_vectors:
            topic = "Unknown"
        else:
            # Summarize
            topic = llm.summarize(cluster_events)

        summarized_clusters[int(label)] = {
            "event_ids": ids,
            "topic": topic,
            "count": len(ids),
        }

    return {
        "cluster_count": cluster_count,
        "total_events": len(event_ids),
        "noise_count": list(labels).count(-1),
        "clusters": summarized_clusters,
    }


def compute_anomalies(window_hours=1, contamination=0.01):
    """Detect semantic anomalies in the last window"""
    wc = WeaviateClient()
    llm = LLMClient()
    con = get_db_connection()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    collection = wc.client.collections.get("EventEmbedding")
    response = collection.query.fetch_objects(
        filters=wvq.Filter.by_property("timestamp").greater_or_equal(window_start),
        limit=1000,
        include_vector=True,
    )
    wc.close()

    if len(response.objects) < 10:
        return {"anomaly_count": 0, "reason": "insufficient_data"}

    vectors = np.array([obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response.objects])

    # Isolation Forest
    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(vectors)

    # -1 is anomaly
    anomaly_indices = [i for i, x in enumerate(preds) if x == -1]

    anomalies = []
    for idx in anomaly_indices:
        obj = response.objects[idx]
        event_id = obj.properties["event_id"]

        # Get neighbors for explanation
        # We can use the vectors to find nearest neighbors in the same set
        # Simple approach: calculate distance to all others, pick top 3
        # Or just ask Weaviate for nearest neighbors of this ID?
        # Let's use the local vectors for speed since we have them

        # Explain
        # For explanation, we need text.
        # Fetch text from DuckDB if not in properties (properties has source, maybe text?)
        # Weaviate schema has source, event_id, timestamp. No text.
        # Need to fetch text from DuckDB.

        row = con.execute(
            "SELECT text_payload FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        text_payload = row[0] if row else ""

        event_data = {
            "text_payload": text_payload,
            "source": obj.properties.get("source"),
        }

        # Mock neighbors for now (random normal points)
        normal_indices = [i for i, x in enumerate(preds) if x == 1]
        if normal_indices:
            neighbor_idx = normal_indices[:3]  # Just take first 3 normal ones
            neighbor_objs = [response.objects[i] for i in neighbor_idx]
            neighbor_ids = [o.properties["event_id"] for o in neighbor_objs]

            # Fetch neighbor texts
            placeholders = ",".join(["?"] * len(neighbor_ids))
            rows = con.execute(
                f"SELECT text_payload FROM events WHERE event_id IN ({placeholders})",
                neighbor_ids,
            ).fetchall()
            neighbor_data = [{"text_payload": r[0]} for r in rows]
        else:
            neighbor_data = []

        explanation = llm.explain_anomaly(event_data, neighbor_data)

        # Persist
        con.execute(
            "INSERT INTO anomalies (event_id, score, explanation, created_at) VALUES (?, ?, ?, current_timestamp)",
            (event_id, -1.0, explanation),  # Score -1 for now
        )

        anomalies.append(
            {"event_id": event_id, "explanation": explanation, "text": text_payload}
        )

    return {"anomaly_count": len(anomalies), "anomalies": anomalies}


def compute_projection(window_hours=1, method="pca", n_components=2):
    """Project embeddings to 2D/3D for visualization"""
    wc = WeaviateClient()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    try:
        collection = wc.client.collections.get("EventEmbedding")
        response = collection.query.fetch_objects(
            filters=wvq.Filter.by_property("timestamp").greater_or_equal(window_start),
            limit=2000,  # Limit for viz
            include_vector=True,
        )
    except Exception as e:
        print(f"Weaviate error in compute_projection: {e}")
        wc.close()
        return []
    wc.close()

    if not response.objects:
        return []

    vectors = np.array([obj.vector['default'] if isinstance(obj.vector, dict) else obj.vector for obj in response.objects])
    event_ids = [obj.properties["event_id"] for obj in response.objects]
    sources = [obj.properties.get("source", "unknown") for obj in response.objects]

    if len(vectors) < 3:
        # Not enough for reduction, just return 0s or raw if low dim (but they are high dim)
        # Return empty or mock
        return []

    projection = None
    if method == "umap" and umap is not None:
        try:
            reducer = umap.UMAP(n_components=n_components, random_state=42)
            projection = reducer.fit_transform(vectors)
        except Exception as e:
            print(f"UMAP failed, falling back to PCA: {e}")
            method = "pca"

    if method == "pca" or projection is None:
        pca = PCA(n_components=n_components)
        projection = pca.fit_transform(vectors)

    results = []
    for i, eid in enumerate(event_ids):
        results.append(
            {
                "event_id": eid,
                "x": float(projection[i, 0]),
                "y": float(projection[i, 1]),
                "z": float(projection[i, 2]) if n_components > 2 else 0.0,
                "source": sources[i],
            }
        )

    return results


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

            # Compute anomalies
            anomalies = compute_anomalies(window_hours=1)
            r.set("tvos:hot:anomalies:1h", json.dumps(anomalies), ex=3600)
            ANOMALY_COUNT.set(anomalies.get("anomaly_count", 0))
            print(f"  Anomalies: {anomalies.get('anomaly_count', 0)}")

            ANALYTICS_RUNS.inc()

        except Exception as e:
            print(f"Error in analytics: {e}")
            traceback.print_exc()

        time.sleep(interval_seconds)
