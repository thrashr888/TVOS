#!/usr/bin/env python3
"""Test embedding worker flow"""
import redis
from tvos.config import Config

# Check Redis queue
r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)
queue_length = r.llen("tvos:queue:embedding")
print(f"Queue length: {queue_length}")

if queue_length > 0:
    # Peek at items
    items = r.lrange("tvos:queue:embedding", 0, -1)
    print(f"Items in queue: {items}")
