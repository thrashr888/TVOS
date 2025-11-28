#!/usr/bin/env python3
"""Check embeddings"""
import duckdb
from tvos.config import Config
from tvos.weaviate_client import WeaviateClient

# Check DuckDB
con = duckdb.connect(Config.DUCKDB_PATH, read_only=True)
result = con.execute("SELECT count(*) FROM events WHERE embedding_id IS NOT NULL").fetchone()
print(f"Events with embeddings in DuckDB: {result[0]}")

result = con.execute("SELECT count(*) FROM embeddings").fetchone()
print(f"Embeddings table count: {result[0]}")
con.close()

# Check Weaviate
try:
    wc = WeaviateClient()
    collection = wc.client.collections.get("EventEmbedding")
    count = len(collection.query.fetch_objects(limit=100).objects)
    print(f"Vectors in Weaviate: {count}")
    wc.close()
except Exception as e:
    print(f"Error checking Weaviate: {e}")
