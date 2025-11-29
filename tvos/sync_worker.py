"""
Sync worker for external connectors.
Polls for scheduled and manual sync jobs and executes them.
"""

import time
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from prometheus_client import Counter, Histogram

from tvos.config import Config
from tvos.db import get_db_connection
from tvos.connectors import ConnectorRegistry, SyncScheduler, SyncJobStatus
from tvos.protos.events_pb2 import EventPayload

# Metrics
SYNC_JOBS_EXECUTED = Counter("tvos_sync_jobs_total", "Total sync jobs executed", ["connector", "status"])
SYNC_JOB_LATENCY = Histogram("tvos_sync_job_latency_seconds", "Time spent executing sync job", ["connector"])
SYNC_EVENTS_FETCHED = Counter("tvos_sync_events_fetched_total", "Total events fetched from connectors", ["connector"])


def run_sync_worker(registry: Optional[ConnectorRegistry] = None, scheduler: Optional[SyncScheduler] = None):
    """
    Main sync worker loop.
    Polls for pending sync jobs and executes them.
    
    Args:
        registry: ConnectorRegistry instance (created if None)
        scheduler: SyncScheduler instance (created if None)
    """
    if registry is None:
        registry = ConnectorRegistry()
    
    if scheduler is None:
        scheduler = SyncScheduler()
    
    print("Sync worker started")
    
    # Poll interval in seconds
    poll_interval = 5
    
    while True:
        try:
            # Get pending jobs that are ready to run
            pending_jobs = scheduler.get_pending_jobs(limit=10)
            
            if not pending_jobs:
                # No jobs to process, sleep and continue
                time.sleep(poll_interval)
                continue
            
            # Process each pending job
            for job in pending_jobs:
                try:
                    execute_sync_job(job, registry, scheduler)
                except Exception as e:
                    print(f"Error executing sync job {job['job_id']}: {e}")
                    # Continue with next job even if this one fails
                    continue
            
            # Brief sleep between job batches
            time.sleep(1)
            
        except Exception as e:
            print(f"Error in sync worker loop: {e}")
            time.sleep(poll_interval)


def execute_sync_job(
    job: Dict[str, Any],
    registry: ConnectorRegistry,
    scheduler: SyncScheduler
) -> None:
    """
    Execute a single sync job with error handling and retry logic.
    
    Args:
        job: Job dictionary from get_pending_jobs
        registry: ConnectorRegistry instance
        scheduler: SyncScheduler instance
    """
    job_id = job['job_id']
    connector_name = job['connector_name']
    user_id = job['user_id']
    
    start_time = time.time()
    
    try:
        # Update job status to running
        scheduler.update_job_status(job_id, SyncJobStatus.RUNNING)
        
        # Get connector instance
        connector = registry.get_connector(connector_name)
        if not connector:
            raise ValueError(f"Connector '{connector_name}' not found in registry")
        
        # Get credentials
        credentials = registry.get_credentials(connector_name, user_id)
        if not credentials:
            raise ValueError(f"No credentials found for connector '{connector_name}'")
        
        # Get last sync timestamp from sync_state
        conn = get_db_connection()
        sync_state_row = conn.execute(
            """
            SELECT last_sync_timestamp FROM sync_state
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        since = None
        if sync_state_row and sync_state_row[0]:
            # Convert milliseconds to datetime
            since = datetime.fromtimestamp(sync_state_row[0] / 1000.0)
        
        # Get connector configuration for filters
        config_row = conn.execute(
            """
            SELECT filters FROM connector_configs
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        filters = None
        if config_row and config_row[0]:
            filters = json.loads(config_row[0])
        
        # Fetch events from external service with retry logic
        print(f"Fetching events for {connector_name} since {since}")
        raw_events = fetch_with_retry(connector, credentials, since, filters, connector_name)
        
        print(f"Fetched {len(raw_events)} events from {connector_name}")
        
        # Transform and inject events into TVOS pipeline
        events_synced = 0
        for raw_event in raw_events:
            try:
                # Transform to EventPayload
                event_payload = connector.transform_event(raw_event)
                
                # Inject into database (same as ingest worker)
                inject_event(event_payload)
                
                events_synced += 1
                SYNC_EVENTS_FETCHED.inc(labels=[connector_name])
                
            except Exception as e:
                print(f"Error transforming/injecting event from {connector_name}: {e}")
                # Continue with next event - don't fail entire sync for one bad event
                continue
        
        # Update job status to completed
        scheduler.update_job_status(
            job_id,
            SyncJobStatus.COMPLETED,
            events_synced=events_synced
        )
        
        # Record metrics
        elapsed = time.time() - start_time
        SYNC_JOB_LATENCY.observe(elapsed, labels=[connector_name])
        SYNC_JOBS_EXECUTED.inc(labels=[connector_name, "completed"])
        
        print(f"Sync job {job_id} completed: {events_synced} events synced in {elapsed:.2f}s")
        
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (authentication, rate limiting, etc.)
        error_message = handle_http_error(e, connector_name, user_id)
        print(f"Sync job {job_id} failed with HTTP error: {error_message}")
        
        try:
            scheduler.update_job_status(
                job_id,
                SyncJobStatus.FAILED,
                error_message=error_message
            )
            SYNC_JOBS_EXECUTED.inc(labels=[connector_name, "failed"])
        except Exception as update_error:
            print(f"Error updating job status to failed: {update_error}")
    
    except requests.exceptions.RequestException as e:
        # Handle network errors
        error_message = f"Network error: {str(e)}"
        print(f"Sync job {job_id} failed with network error: {error_message}")
        
        try:
            scheduler.update_job_status(
                job_id,
                SyncJobStatus.FAILED,
                error_message=error_message
            )
            SYNC_JOBS_EXECUTED.inc(labels=[connector_name, "failed"])
        except Exception as update_error:
            print(f"Error updating job status to failed: {update_error}")
    
    except Exception as e:
        # Catch all other exceptions to prevent worker crash
        error_message = f"Unexpected error: {str(e)}"
        print(f"Sync job {job_id} failed: {error_message}")
        
        try:
            scheduler.update_job_status(
                job_id,
                SyncJobStatus.FAILED,
                error_message=error_message
            )
            SYNC_JOBS_EXECUTED.inc(labels=[connector_name, "failed"])
        except Exception as update_error:
            print(f"Error updating job status to failed: {update_error}")


def fetch_with_retry(
    connector,
    credentials: Dict[str, Any],
    since: Optional[datetime],
    filters: Optional[Dict[str, Any]],
    connector_name: str,
    max_retries: int = 3
) -> list:
    """
    Fetch events with exponential backoff retry logic for transient errors.
    
    Args:
        connector: Connector instance
        credentials: Decrypted credentials
        since: Last sync timestamp
        filters: Connector-specific filters
        connector_name: Name of connector (for logging)
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of raw events
        
    Raises:
        Exception: If all retries fail
    """
    retry_count = 0
    base_delay = 1  # Start with 1 second
    
    while retry_count <= max_retries:
        try:
            return connector.fetch_events(credentials, since=since, filters=filters)
        
        except requests.exceptions.HTTPError as e:
            # Don't retry authentication errors or client errors (4xx except 429)
            if e.response is not None:
                status_code = e.response.status_code
                
                # Authentication errors - don't retry
                if status_code in [401, 403]:
                    raise
                
                # Rate limiting - retry with backoff
                if status_code == 429:
                    retry_after = e.response.headers.get('Retry-After')
                    if retry_after:
                        delay = int(retry_after)
                    else:
                        delay = base_delay * (2 ** retry_count)
                    
                    print(f"Rate limited on {connector_name}, retrying after {delay}s (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(delay)
                    retry_count += 1
                    continue
                
                # Other 4xx errors - don't retry
                if 400 <= status_code < 500:
                    raise
            
            # 5xx errors or unknown - retry with backoff
            if retry_count < max_retries:
                delay = base_delay * (2 ** retry_count)
                print(f"HTTP error on {connector_name}, retrying after {delay}s (attempt {retry_count + 1}/{max_retries}): {e}")
                time.sleep(delay)
                retry_count += 1
            else:
                raise
        
        except requests.exceptions.RequestException as e:
            # Network errors - retry with exponential backoff
            if retry_count < max_retries:
                delay = base_delay * (2 ** retry_count)
                print(f"Network error on {connector_name}, retrying after {delay}s (attempt {retry_count + 1}/{max_retries}): {e}")
                time.sleep(delay)
                retry_count += 1
            else:
                raise
        
        except Exception as e:
            # Other exceptions - don't retry, let caller handle
            raise
    
    # Should not reach here, but just in case
    raise Exception(f"Failed to fetch events after {max_retries} retries")


def handle_http_error(error: requests.exceptions.HTTPError, connector_name: str, user_id: str) -> str:
    """
    Handle HTTP errors and update connector state accordingly.
    
    Args:
        error: HTTP error exception
        connector_name: Name of the connector
        user_id: User identifier
        
    Returns:
        Error message string
    """
    if error.response is None:
        return f"HTTP error: {str(error)}"
    
    status_code = error.response.status_code
    
    # Authentication errors
    if status_code in [401, 403]:
        # Mark connector as requiring re-authentication
        try:
            conn = get_db_connection()
            
            # Update connector config to indicate re-auth needed
            # We can use metadata field in sync_state for this
            conn.execute(
                """
                UPDATE sync_state
                SET metadata = json_set(COALESCE(metadata, '{}'), '$.requires_reauth', true)
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            )
            
            # Disable auto-sync
            conn.execute(
                """
                UPDATE connector_configs
                SET enabled = FALSE
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            )
            
            print(f"Connector {connector_name} marked as requiring re-authentication")
        except Exception as e:
            print(f"Error marking connector for re-auth: {e}")
        
        return f"Authentication failed (HTTP {status_code}): Connector requires re-authentication"
    
    # Rate limiting
    if status_code == 429:
        return f"Rate limit exceeded (HTTP {status_code})"
    
    # Other errors
    return f"HTTP {status_code}: {error.response.text[:200]}"


def inject_event(event: EventPayload) -> None:
    """
    Inject an event into the TVOS pipeline.
    Similar to ingest worker, but for connector events.
    
    Args:
        event: EventPayload protobuf message
    """
    import redis
    
    conn = get_db_connection()
    
    # Insert into DuckDB
    conn.execute(
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
        r = redis.Redis(
            host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
        )
        r.rpush("tvos:queue:embedding", event.event_id)
        r.close()
    
    # Publish to Redis for real-time UI
    r = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True
    )
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
    r.close()
