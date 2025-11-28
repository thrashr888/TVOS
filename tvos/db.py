import duckdb
import json
from tvos.config import Config

# Global singleton connection
_SHARED_CONN = None


def get_db_connection():
    """
    Returns a shared DuckDB connection.
    DuckDB connections are thread-safe, and using a single connection prevents
    file locking conflicts (e.g. read_only vs read_write mismatches).
    """
    global _SHARED_CONN
    if _SHARED_CONN is None:
        print(f"Initializing shared DuckDB connection to {Config.DUCKDB_PATH}")
        # Open in read-write mode (default)
        _SHARED_CONN = duckdb.connect(Config.DUCKDB_PATH, read_only=False)
    return _SHARED_CONN


def init_db():
    con = get_db_connection()

    # Events table
    con.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id VARCHAR PRIMARY KEY,
            timestamp_ms BIGINT,
            source VARCHAR,
            text_payload VARCHAR,
            metrics JSON,
            metadata JSON,
            embedding_id VARCHAR
        )
    """)

    # Embeddings table (metadata only, vectors in Weaviate)
    con.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            embedding_id VARCHAR PRIMARY KEY,
            vector_dim INTEGER,
            created_at TIMESTAMP
        )
    """)

    # Do NOT close the shared connection
    # con.close()


if __name__ == "__main__":
    init_db()
