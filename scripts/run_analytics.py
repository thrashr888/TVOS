#!/usr/bin/env python3
"""Trigger analytics computation once"""
import sys
sys.path.insert(0, '.')

from tvos.analytics import compute_windowed_stats, compute_semantic_drift, compute_clusters
import redis
import json
from tvos.config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

print("Computing windowed stats...")
stats = compute_windowed_stats(window_hours=1)
r.set('tvos:hot:stats:1h', json.dumps(stats), ex=3600)
print(f"Stats: {stats}")

print("\nComputing semantic drift...")
drift = compute_semantic_drift(window_hours=1)
r.set('tvos:hot:drift:1h', json.dumps(drift), ex=3600)
print(f"Drift: {drift}")

print("\nComputing clusters...")
clusters = compute_clusters(window_hours=24, min_cluster_size=3)
r.set('tvos:hot:clusters:24h', json.dumps(clusters), ex=86400)
print(f"Clusters: {clusters}")

print("\nDone! Results stored in Redis.")
