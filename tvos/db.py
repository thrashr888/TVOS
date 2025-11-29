import duckdb
import json
import threading
from tvos.config import Config

# Global singleton connection
_SHARED_CONN = None
_DB_LOCK = threading.Lock()


def get_db_connection():
    """
    Returns a shared DuckDB connection.
    DuckDB connections are thread-safe, and using a single connection prevents
    file locking conflicts (e.g. read_only vs read_write mismatches).
    """
    global _SHARED_CONN
    with _DB_LOCK:
        if _SHARED_CONN is None:
            print(f"Initializing shared DuckDB connection to {Config.DUCKDB_PATH}")
            # Open in read-write mode (default)
            try:
                _SHARED_CONN = duckdb.connect(Config.DUCKDB_PATH, read_only=False)
            except Exception as e:
                print(f"Error connecting to DuckDB: {e}")
                raise e
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

    # Drift History table
    con.execute("""
        CREATE TABLE IF NOT EXISTS drift_history (
            timestamp_ms BIGINT,
            score DOUBLE,
            window_hours INTEGER
        )
    """)

    # Anomalies table
    con.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            event_id VARCHAR,
            score DOUBLE,
            explanation TEXT,
            created_at TIMESTAMP
        )
    """)

    # Connector configurations table
    con.execute("""
        CREATE TABLE IF NOT EXISTS connector_configs (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            connector_name VARCHAR,
            enabled BOOLEAN,
            sync_interval_minutes INTEGER,
            filters JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # Encrypted credentials table
    con.execute("""
        CREATE TABLE IF NOT EXISTS connector_credentials (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            connector_name VARCHAR,
            encrypted_data BLOB,
            iv BLOB,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # Sync job history
    con.execute("""
        CREATE TABLE IF NOT EXISTS sync_jobs (
            job_id VARCHAR PRIMARY KEY,
            connector_name VARCHAR,
            user_id VARCHAR,
            status VARCHAR,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            events_synced INTEGER,
            error_message TEXT,
            sync_type VARCHAR
        )
    """)

    # Sync state (cursor/checkpoint for incremental sync)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            connector_name VARCHAR,
            user_id VARCHAR,
            last_sync_timestamp BIGINT,
            cursor VARCHAR,
            metadata JSON,
            PRIMARY KEY (connector_name, user_id)
        )
    """)

    # Create indexes for performance optimization
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_connector_configs_user_connector 
        ON connector_configs(user_id, connector_name)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_connector_credentials_user_connector 
        ON connector_credentials(user_id, connector_name)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_connector_status 
        ON sync_jobs(connector_name, status)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_user 
        ON sync_jobs(user_id)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_state_last_sync 
        ON sync_state(last_sync_timestamp)
    """)

    # Do NOT close the shared connection
    # con.close()


if __name__ == "__main__":
    init_db()
