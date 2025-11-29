"""
External connector infrastructure for TVOS.
Provides base classes, credential encryption, and connector registry.
"""

import json
import os
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import base64
from urllib.parse import urlencode
import requests

from tvos.config import Config
from tvos.protos.events_pb2 import EventPayload


class CredentialEncryption:
    """
    Handles encryption and decryption of connector credentials using AES-256-GCM.
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption with a key.
        
        Args:
            key: Base64-encoded 32-byte key. If None, uses Config.CONNECTOR_ENCRYPTION_KEY
        """
        if key is None:
            key = Config.CONNECTOR_ENCRYPTION_KEY
        
        if not key:
            raise ValueError(
                "Encryption key not configured. Set CONNECTOR_ENCRYPTION_KEY environment variable."
            )
        
        try:
            # Decode base64 key
            self.key = base64.b64decode(key)
            if len(self.key) != 32:
                raise ValueError("Encryption key must be 32 bytes (256 bits)")
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
        
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, credentials: Dict[str, Any]) -> tuple[bytes, bytes]:
        """
        Encrypt credentials dictionary.
        
        Args:
            credentials: Dictionary containing credential data
            
        Returns:
            Tuple of (encrypted_data, iv) as bytes
        """
        # Convert credentials to JSON string
        plaintext = json.dumps(credentials).encode('utf-8')
        
        # Generate random 12-byte nonce (IV)
        iv = os.urandom(12)
        
        # Encrypt with AES-256-GCM
        encrypted_data = self.aesgcm.encrypt(iv, plaintext, None)
        
        return encrypted_data, iv

    def decrypt(self, encrypted_data: bytes, iv: bytes) -> Dict[str, Any]:
        """
        Decrypt credentials.
        
        Args:
            encrypted_data: Encrypted credential data
            iv: Initialization vector used during encryption
            
        Returns:
            Decrypted credentials dictionary
        """
        # Decrypt
        plaintext = self.aesgcm.decrypt(iv, encrypted_data, None)
        
        # Parse JSON
        credentials = json.loads(plaintext.decode('utf-8'))
        
        return credentials

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random 256-bit encryption key.
        
        Returns:
            Base64-encoded key suitable for CONNECTOR_ENCRYPTION_KEY
        """
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode('utf-8')


class ConnectorBase(ABC):
    """Base class for all external connectors"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique connector identifier (e.g., 'gmail', 'github')"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Gmail', 'GitHub')"""
        pass
    
    @abstractmethod
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Returns OAuth URL for user authentication.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            OAuth authorization URL
        """
        pass
    
    @abstractmethod
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges auth code for credentials.
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            Dictionary containing access_token, refresh_token, etc.
        """
        pass
    
    @abstractmethod
    def fetch_events(
        self, 
        credentials: Dict[str, Any],
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches events from external service.
        
        Args:
            credentials: Decrypted credentials dictionary
            since: Only fetch events after this timestamp
            filters: Connector-specific filters
            
        Returns:
            List of raw external events
        """
        pass
    
    @abstractmethod
    def transform_event(self, raw_event: Dict[str, Any]) -> 'EventPayload':
        """
        Transforms external event to TVOS EventPayload.
        
        Args:
            raw_event: Raw event from external service
            
        Returns:
            EventPayload protobuf message
        """
        pass
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validates that credentials are still valid.
        
        Args:
            credentials: Credentials to validate
            
        Returns:
            True if credentials are valid, False otherwise
        """
        return True
    
    def get_rate_limit_info(self) -> Dict[str, int]:
        """
        Returns rate limit information for this connector.
        
        Returns:
            Dictionary with rate limit details
        """
        return {"requests_per_hour": 1000, "requests_per_day": 10000}
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validates connector configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        # Default implementation - subclasses can override
        return True
    
    def handle_rate_limit(self, retry_after: Optional[int] = None) -> int:
        """
        Calculate backoff delay for rate limiting.
        
        Args:
            retry_after: Suggested retry delay from API (seconds)
            
        Returns:
            Delay in seconds before next retry
        """
        if retry_after:
            return retry_after
        # Default exponential backoff: start with 60 seconds
        return 60


class ConnectorRegistry:
    """
    Central registry for all connectors.
    Manages connector lifecycle, configuration, and credential storage.
    """

    def __init__(self):
        """Initialize the connector registry."""
        self._connectors: Dict[str, ConnectorBase] = {}
        self._crypto = CredentialEncryption()
        # Import here to avoid circular dependency
        from tvos.db import get_db_connection
        self._get_db = get_db_connection

    def register(self, connector: ConnectorBase) -> None:
        """
        Register a new connector type.
        
        Args:
            connector: Connector instance to register
            
        Raises:
            ValueError: If connector with same name already registered
        """
        if connector.name in self._connectors:
            raise ValueError(f"Connector '{connector.name}' is already registered")
        
        # Validate that connector implements required methods
        required_methods = ['get_auth_url', 'authenticate', 'fetch_events', 'transform_event']
        for method_name in required_methods:
            if not hasattr(connector, method_name) or not callable(getattr(connector, method_name)):
                raise ValueError(
                    f"Connector '{connector.name}' must implement method '{method_name}'"
                )
        
        self._connectors[connector.name] = connector

    def get_connector(self, name: str) -> Optional[ConnectorBase]:
        """
        Get connector instance by name.
        
        Args:
            name: Connector name (e.g., 'gmail', 'github')
            
        Returns:
            Connector instance or None if not found
        """
        return self._connectors.get(name)

    def list_connectors(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """
        List all available connectors with status information.
        
        Args:
            user_id: User identifier for multi-user support
            
        Returns:
            List of connector status dictionaries
        """
        conn = self._get_db()
        result = []
        
        for connector_name, connector in self._connectors.items():
            # Get configuration
            config_row = conn.execute(
                """
                SELECT enabled, sync_interval_minutes, created_at, updated_at
                FROM connector_configs
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            ).fetchone()
            
            # Check if credentials exist
            cred_row = conn.execute(
                """
                SELECT id FROM connector_credentials
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            ).fetchone()
            
            connected = cred_row is not None
            enabled = False
            sync_interval_minutes = None
            
            if config_row:
                enabled = config_row[0]
                sync_interval_minutes = config_row[1]
            
            # Get last sync timestamp and event count
            sync_state_row = conn.execute(
                """
                SELECT last_sync_timestamp FROM sync_state
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            ).fetchone()
            
            last_sync_timestamp = sync_state_row[0] if sync_state_row else None
            last_sync = None
            if last_sync_timestamp:
                last_sync = datetime.fromtimestamp(last_sync_timestamp / 1000.0)
            
            # Count events from this connector
            event_count = conn.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE source = ?
                """,
                [connector_name]
            ).fetchone()[0]
            
            # Get next sync time (if scheduled)
            next_sync = None
            if enabled and sync_interval_minutes:
                # Find next scheduled job
                next_job = conn.execute(
                    """
                    SELECT started_at FROM sync_jobs
                    WHERE connector_name = ? AND user_id = ? 
                    AND status = 'pending'
                    ORDER BY started_at ASC
                    LIMIT 1
                    """,
                    [connector_name, user_id]
                ).fetchone()
                if next_job:
                    next_sync = next_job[0]
            
            result.append({
                "name": connector_name,
                "display_name": connector.display_name,
                "enabled": enabled,
                "connected": connected,
                "last_sync": last_sync,
                "next_sync": next_sync,
                "event_count": event_count,
                "sync_interval_minutes": sync_interval_minutes
            })
        
        return result

    def save_credentials(
        self, 
        connector_name: str, 
        user_id: str, 
        credentials: Dict[str, Any]
    ) -> None:
        """
        Encrypt and store credentials for a connector.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            credentials: Credentials dictionary to encrypt and store
            
        Raises:
            ValueError: If connector not registered
        """
        if connector_name not in self._connectors:
            raise ValueError(f"Connector '{connector_name}' is not registered")
        
        # Encrypt credentials
        encrypted_data, iv = self._crypto.encrypt(credentials)
        
        # Generate ID
        cred_id = f"{user_id}:{connector_name}"
        
        conn = self._get_db()
        now = datetime.now()
        
        # Check if credentials already exist
        existing = conn.execute(
            """
            SELECT id FROM connector_credentials
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        if existing:
            # Update existing credentials
            conn.execute(
                """
                UPDATE connector_credentials
                SET encrypted_data = ?, iv = ?, updated_at = ?
                WHERE connector_name = ? AND user_id = ?
                """,
                [encrypted_data, iv, now, connector_name, user_id]
            )
        else:
            # Insert new credentials
            conn.execute(
                """
                INSERT INTO connector_credentials 
                (id, user_id, connector_name, encrypted_data, iv, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [cred_id, user_id, connector_name, encrypted_data, iv, now, now]
            )

    def get_credentials(
        self, 
        connector_name: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt credentials for a connector.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            
        Returns:
            Decrypted credentials dictionary or None if not found
            
        Raises:
            ValueError: If decryption fails
        """
        conn = self._get_db()
        
        row = conn.execute(
            """
            SELECT encrypted_data, iv FROM connector_credentials
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        if not row:
            return None
        
        encrypted_data, iv = row
        
        try:
            credentials = self._crypto.decrypt(encrypted_data, iv)
            return credentials
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {e}")

    def delete_credentials(self, connector_name: str, user_id: str) -> None:
        """
        Remove stored credentials for a connector.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
        """
        conn = self._get_db()
        
        conn.execute(
            """
            DELETE FROM connector_credentials
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        )

    def get_connector_status(
        self, 
        connector_name: str, 
        user_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed status for a specific connector.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            
        Returns:
            Status dictionary with all required fields or None if not found
        """
        if connector_name not in self._connectors:
            return None
        
        connector = self._connectors[connector_name]
        conn = self._get_db()
        
        # Get configuration
        config_row = conn.execute(
            """
            SELECT enabled, sync_interval_minutes, filters, created_at, updated_at
            FROM connector_configs
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        # Check if credentials exist
        cred_row = conn.execute(
            """
            SELECT id FROM connector_credentials
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        connected = cred_row is not None
        enabled = False
        sync_interval_minutes = None
        filters = None
        
        if config_row:
            enabled = config_row[0]
            sync_interval_minutes = config_row[1]
            filters = json.loads(config_row[2]) if config_row[2] else None
        
        # Get last sync timestamp
        sync_state_row = conn.execute(
            """
            SELECT last_sync_timestamp, cursor, metadata FROM sync_state
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        last_sync_timestamp = None
        last_sync = None
        cursor = None
        sync_metadata = None
        
        if sync_state_row:
            last_sync_timestamp = sync_state_row[0]
            cursor = sync_state_row[1]
            sync_metadata = json.loads(sync_state_row[2]) if sync_state_row[2] else None
            if last_sync_timestamp:
                last_sync = datetime.fromtimestamp(last_sync_timestamp / 1000.0)
        
        # Count events from this connector
        event_count = conn.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE source = ?
            """,
            [connector_name]
        ).fetchone()[0]
        
        return {
            "name": connector_name,
            "display_name": connector.display_name,
            "enabled": enabled,
            "connected": connected,
            "last_sync": last_sync,
            "last_sync_timestamp": last_sync_timestamp,
            "event_count": event_count,
            "sync_interval_minutes": sync_interval_minutes,
            "filters": filters,
            "cursor": cursor,
            "sync_metadata": sync_metadata
        }

    def disconnect(self, connector_name: str, user_id: str = "default") -> None:
        """
        Disconnect a connector by removing credentials and disabling it.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            
        Raises:
            ValueError: If connector not registered
        """
        if connector_name not in self._connectors:
            raise ValueError(f"Connector '{connector_name}' is not registered")
        
        conn = self._get_db()
        
        # Delete credentials
        self.delete_credentials(connector_name, user_id)
        
        # Disable connector in config
        conn.execute(
            """
            UPDATE connector_configs
            SET enabled = FALSE, updated_at = ?
            WHERE connector_name = ? AND user_id = ?
            """,
            [datetime.now(), connector_name, user_id]
        )


class SyncJobStatus(str, Enum):
    """Enumeration of sync job states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncScheduler:
    """
    Manages scheduled and manual sync jobs.
    Implements a state machine for job lifecycle management.
    """
    
    # Valid state transitions
    _VALID_TRANSITIONS = {
        SyncJobStatus.PENDING: {SyncJobStatus.RUNNING, SyncJobStatus.CANCELLED},
        SyncJobStatus.RUNNING: {SyncJobStatus.COMPLETED, SyncJobStatus.FAILED, SyncJobStatus.CANCELLED},
        SyncJobStatus.COMPLETED: set(),  # Terminal state
        SyncJobStatus.FAILED: set(),  # Terminal state
        SyncJobStatus.CANCELLED: set(),  # Terminal state
    }
    
    def __init__(self):
        """Initialize the sync scheduler."""
        # Import here to avoid circular dependency
        from tvos.db import get_db_connection
        self._get_db = get_db_connection
    
    def schedule_sync(
        self, 
        connector_name: str,
        user_id: str,
        interval_minutes: int
    ) -> str:
        """
        Schedule periodic sync job.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            interval_minutes: Sync interval in minutes
            
        Returns:
            job_id: Unique identifier for the scheduled job
            
        Raises:
            ValueError: If connector is not enabled or invalid interval
        """
        if interval_minutes <= 0:
            raise ValueError("Sync interval must be positive")
        
        conn = self._get_db()
        
        # Verify connector is enabled
        config_row = conn.execute(
            """
            SELECT enabled FROM connector_configs
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        if not config_row or not config_row[0]:
            raise ValueError(f"Connector '{connector_name}' is not enabled")
        
        # Generate job ID
        job_id = f"sync_{connector_name}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Calculate next sync time based on last sync or now
        sync_state_row = conn.execute(
            """
            SELECT last_sync_timestamp FROM sync_state
            WHERE connector_name = ? AND user_id = ?
            """,
            [connector_name, user_id]
        ).fetchone()
        
        if sync_state_row and sync_state_row[0]:
            # Schedule from last sync time
            last_sync = datetime.fromtimestamp(sync_state_row[0] / 1000.0)
            next_sync = last_sync + timedelta(minutes=interval_minutes)
            # If next sync is in the past, schedule for now
            if next_sync < datetime.now():
                next_sync = datetime.now()
        else:
            # No previous sync, schedule for now
            next_sync = datetime.now()
        
        # Create sync job
        conn.execute(
            """
            INSERT INTO sync_jobs 
            (job_id, connector_name, user_id, status, started_at, completed_at, 
             events_synced, error_message, sync_type)
            VALUES (?, ?, ?, ?, ?, NULL, 0, NULL, 'scheduled')
            """,
            [job_id, connector_name, user_id, SyncJobStatus.PENDING.value, next_sync]
        )
        
        return job_id
    
    def trigger_manual_sync(
        self,
        connector_name: str,
        user_id: str
    ) -> str:
        """
        Trigger immediate sync job.
        
        Args:
            connector_name: Name of the connector
            user_id: User identifier
            
        Returns:
            job_id: Unique identifier for the sync job
            
        Raises:
            ValueError: If a sync is already running for this connector
        """
        conn = self._get_db()
        
        # Check for running sync jobs
        running_job = conn.execute(
            """
            SELECT job_id FROM sync_jobs
            WHERE connector_name = ? AND user_id = ? AND status = ?
            """,
            [connector_name, user_id, SyncJobStatus.RUNNING.value]
        ).fetchone()
        
        if running_job:
            raise ValueError(
                f"Sync already running for connector '{connector_name}' (job_id: {running_job[0]})"
            )
        
        # Generate job ID
        job_id = f"sync_{connector_name}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Create sync job with immediate start time
        now = datetime.now()
        conn.execute(
            """
            INSERT INTO sync_jobs 
            (job_id, connector_name, user_id, status, started_at, completed_at, 
             events_synced, error_message, sync_type)
            VALUES (?, ?, ?, ?, ?, NULL, 0, NULL, 'manual')
            """,
            [job_id, connector_name, user_id, SyncJobStatus.PENDING.value, now]
        )
        
        return job_id
    
    def cancel_sync(self, job_id: str) -> bool:
        """
        Cancel running or scheduled sync job.
        
        Args:
            job_id: Unique identifier of the sync job
            
        Returns:
            True if job was cancelled, False if job not found or already terminal
            
        Raises:
            ValueError: If state transition is invalid
        """
        conn = self._get_db()
        
        # Get current job status
        job_row = conn.execute(
            """
            SELECT status FROM sync_jobs
            WHERE job_id = ?
            """,
            [job_id]
        ).fetchone()
        
        if not job_row:
            return False
        
        current_status = SyncJobStatus(job_row[0])
        
        # Check if cancellation is valid
        if not self._is_valid_transition(current_status, SyncJobStatus.CANCELLED):
            # Already in terminal state
            return False
        
        # Update job status to cancelled
        now = datetime.now()
        conn.execute(
            """
            UPDATE sync_jobs
            SET status = ?, completed_at = ?
            WHERE job_id = ?
            """,
            [SyncJobStatus.CANCELLED.value, now, job_id]
        )
        
        return True
    
    def get_sync_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of sync job.
        
        Args:
            job_id: Unique identifier of the sync job
            
        Returns:
            Dictionary with job status information or None if not found
        """
        conn = self._get_db()
        
        job_row = conn.execute(
            """
            SELECT job_id, connector_name, user_id, status, started_at, 
                   completed_at, events_synced, error_message, sync_type
            FROM sync_jobs
            WHERE job_id = ?
            """,
            [job_id]
        ).fetchone()
        
        if not job_row:
            return None
        
        return {
            "job_id": job_row[0],
            "connector_name": job_row[1],
            "user_id": job_row[2],
            "status": job_row[3],
            "started_at": job_row[4],
            "completed_at": job_row[5],
            "events_synced": job_row[6],
            "error_message": job_row[7],
            "sync_type": job_row[8]
        }
    
    def update_job_status(
        self,
        job_id: str,
        new_status: SyncJobStatus,
        events_synced: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update sync job status with validation.
        
        Args:
            job_id: Unique identifier of the sync job
            new_status: New status to transition to
            events_synced: Number of events synced (optional)
            error_message: Error message if failed (optional)
            
        Raises:
            ValueError: If job not found or state transition is invalid
        """
        conn = self._get_db()
        
        # Get current job status
        job_row = conn.execute(
            """
            SELECT status, connector_name, user_id FROM sync_jobs
            WHERE job_id = ?
            """,
            [job_id]
        ).fetchone()
        
        if not job_row:
            raise ValueError(f"Sync job '{job_id}' not found")
        
        current_status = SyncJobStatus(job_row[0])
        connector_name = job_row[1]
        user_id = job_row[2]
        
        # Validate state transition
        if not self._is_valid_transition(current_status, new_status):
            raise ValueError(
                f"Invalid state transition from {current_status.value} to {new_status.value}"
            )
        
        # Prepare update
        now = datetime.now()
        completed_at = None
        
        # Set completion time for terminal states
        if new_status in {SyncJobStatus.COMPLETED, SyncJobStatus.FAILED, SyncJobStatus.CANCELLED}:
            completed_at = now
        
        # Update job
        conn.execute(
            """
            UPDATE sync_jobs
            SET status = ?, 
                completed_at = ?,
                events_synced = COALESCE(?, events_synced),
                error_message = ?
            WHERE job_id = ?
            """,
            [new_status.value, completed_at, events_synced, error_message, job_id]
        )
        
        # Update sync state timestamp if completed successfully
        if new_status == SyncJobStatus.COMPLETED:
            timestamp_ms = int(now.timestamp() * 1000)
            
            # Check if sync state exists
            existing = conn.execute(
                """
                SELECT connector_name FROM sync_state
                WHERE connector_name = ? AND user_id = ?
                """,
                [connector_name, user_id]
            ).fetchone()
            
            if existing:
                conn.execute(
                    """
                    UPDATE sync_state
                    SET last_sync_timestamp = ?
                    WHERE connector_name = ? AND user_id = ?
                    """,
                    [timestamp_ms, connector_name, user_id]
                )
            else:
                conn.execute(
                    """
                    INSERT INTO sync_state 
                    (connector_name, user_id, last_sync_timestamp, cursor, metadata)
                    VALUES (?, ?, ?, NULL, NULL)
                    """,
                    [connector_name, user_id, timestamp_ms]
                )
    
    def _is_valid_transition(
        self, 
        current_status: SyncJobStatus, 
        new_status: SyncJobStatus
    ) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            current_status: Current job status
            new_status: Desired new status
            
        Returns:
            True if transition is valid, False otherwise
        """
        if current_status == new_status:
            # Same state is always valid (idempotent)
            return True
        
        valid_next_states = self._VALID_TRANSITIONS.get(current_status, set())
        return new_status in valid_next_states
    
    def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending sync jobs that are ready to run.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries ready for execution
        """
        conn = self._get_db()
        
        now = datetime.now()
        
        jobs = conn.execute(
            """
            SELECT job_id, connector_name, user_id, status, started_at, 
                   completed_at, events_synced, error_message, sync_type
            FROM sync_jobs
            WHERE status = ? AND started_at <= ?
            ORDER BY started_at ASC
            LIMIT ?
            """,
            [SyncJobStatus.PENDING.value, now, limit]
        ).fetchall()
        
        result = []
        for job_row in jobs:
            result.append({
                "job_id": job_row[0],
                "connector_name": job_row[1],
                "user_id": job_row[2],
                "status": job_row[3],
                "started_at": job_row[4],
                "completed_at": job_row[5],
                "events_synced": job_row[6],
                "error_message": job_row[7],
                "sync_type": job_row[8]
            })
        
        return result



class GmailConnector(ConnectorBase):
    """
    Gmail integration using Google OAuth and Gmail API.
    Fetches emails and transforms them into TVOS events.
    """
    
    # OAuth configuration
    OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    REDIRECT_URI = "http://localhost:8000/connectors/gmail/callback"
    
    @property
    def name(self) -> str:
        """Unique connector identifier"""
        return "gmail"
    
    @property
    def display_name(self) -> str:
        """Human-readable name"""
        return "Gmail"
    
    def __init__(self):
        """Initialize Gmail connector with OAuth credentials from config"""
        self.client_id = Config.GMAIL_CLIENT_ID
        self.client_secret = Config.GMAIL_CLIENT_SECRET
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Gmail OAuth credentials not configured. "
                "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables."
            )
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for Gmail.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            OAuth authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }
        
        if state:
            params["state"] = state
        
        return f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        response = requests.post(self.OAUTH_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            raise ValueError(
                f"Failed to exchange auth code: {response.status_code} - {response.text}"
            )
        
        token_data = response.json()
        
        # Validate required fields
        if "access_token" not in token_data:
            raise ValueError("Token response missing access_token")
        
        return token_data
    
    def fetch_events(
        self,
        credentials: Dict[str, Any],
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch Gmail messages since last sync.
        
        Args:
            credentials: Dictionary containing access_token and refresh_token
            since: Only fetch messages after this timestamp
            filters: Optional filters (labels, max_results)
            
        Returns:
            List of Gmail message dictionaries
            
        Raises:
            ValueError: If API request fails
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("Missing access_token in credentials")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        # Build query parameters
        query_parts = []
        
        # Add date filter if provided
        if since:
            # Gmail uses Unix timestamp for after: query
            timestamp = int(since.timestamp())
            query_parts.append(f"after:{timestamp}")
        
        # Add label filters if provided
        if filters and "labels" in filters:
            labels = filters["labels"]
            if isinstance(labels, list):
                for label in labels:
                    query_parts.append(f"label:{label}")
            else:
                query_parts.append(f"label:{labels}")
        
        # Combine query parts
        query = " ".join(query_parts) if query_parts else None
        
        # Determine max results
        max_results = 100  # Default
        if filters and "max_results" in filters:
            max_results = min(filters["max_results"], 500)  # Gmail API limit
        
        # Fetch message list
        messages = []
        page_token = None
        
        while True:
            params = {
                "maxResults": max_results,
            }
            
            if query:
                params["q"] = query
            
            if page_token:
                params["pageToken"] = page_token
            
            # List messages
            list_url = f"{self.GMAIL_API_BASE}/users/me/messages"
            response = requests.get(list_url, headers=headers, params=params)
            
            if response.status_code == 401:
                raise ValueError("Authentication failed - credentials may be expired")
            
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch messages: {response.status_code} - {response.text}"
                )
            
            data = response.json()
            message_list = data.get("messages", [])
            
            # Fetch full message details for each message
            for msg_ref in message_list:
                msg_id = msg_ref["id"]
                msg_url = f"{self.GMAIL_API_BASE}/users/me/messages/{msg_id}"
                msg_response = requests.get(
                    msg_url,
                    headers=headers,
                    params={"format": "full"}
                )
                
                if msg_response.status_code == 200:
                    messages.append(msg_response.json())
            
            # Check for next page
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            
            # Respect pagination limit
            if len(messages) >= max_results:
                break
        
        return messages
    
    def transform_event(self, raw_event: Dict[str, Any]) -> EventPayload:
        """
        Transform Gmail message to TVOS EventPayload.
        
        Args:
            raw_event: Raw Gmail message from API
            
        Returns:
            EventPayload protobuf message
        """
        # Extract message ID
        msg_id = raw_event.get("id", "")
        
        # Extract timestamp (internalDate is in milliseconds)
        timestamp_ms = int(raw_event.get("internalDate", 0))
        
        # Extract headers
        headers = {}
        payload = raw_event.get("payload", {})
        for header in payload.get("headers", []):
            name = header.get("name", "").lower()
            value = header.get("value", "")
            headers[name] = value
        
        # Extract subject, from, to
        subject = headers.get("subject", "(No Subject)")
        from_addr = headers.get("from", "")
        to_addr = headers.get("to", "")
        
        # Extract body (simplified - just get snippet for now)
        snippet = raw_event.get("snippet", "")
        
        # Extract labels
        labels = raw_event.get("labelIds", [])
        
        # Create text payload
        text_payload = f"Subject: {subject}\nFrom: {from_addr}\n\n{snippet}"
        
        # Create EventPayload
        event = EventPayload()
        event.event_id = f"gmail_{msg_id}"
        event.timestamp_ms = timestamp_ms
        event.source = "gmail"
        event.text_payload = text_payload
        
        # Add metadata
        event.metadata["connector"] = "gmail"
        event.metadata["external_id"] = msg_id
        event.metadata["from"] = from_addr
        event.metadata["to"] = to_addr
        event.metadata["subject"] = subject
        event.metadata["labels"] = json.dumps(labels)
        
        return event
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate Gmail credentials by making a test API call.
        
        Args:
            credentials: Credentials to validate
            
        Returns:
            True if credentials are valid, False otherwise
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return False
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        # Make a simple API call to verify credentials
        url = f"{self.GMAIL_API_BASE}/users/me/profile"
        response = requests.get(url, headers=headers)
        
        return response.status_code == 200
    
    def get_rate_limit_info(self) -> Dict[str, int]:
        """
        Return Gmail API rate limit information.
        
        Returns:
            Dictionary with rate limit details
        """
        return {
            "requests_per_second": 250,
            "requests_per_day": 1_000_000_000,  # 1 billion quota units per day
        }



class GmailConnector(ConnectorBase):
    """
    Gmail integration using Google OAuth and Gmail API.
    Fetches emails and transforms them into TVOS events.
    """

    @property
    def name(self) -> str:
        return "gmail"

    @property
    def display_name(self) -> str:
        return "Gmail"

    def __init__(self):
        """Initialize Gmail connector with OAuth configuration."""
        self.client_id = Config.GMAIL_CLIENT_ID
        self.client_secret = Config.GMAIL_CLIENT_SECRET
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        self.redirect_uri = "http://localhost:8000/connectors/gmail/callback"

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Gmail OAuth credentials not configured. "
                "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables."
            )

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for Gmail.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            OAuth authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        if state:
            params["state"] = state

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return auth_url

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If token exchange fails
        """
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            tokens = response.json()

            # Validate required fields
            if "access_token" not in tokens:
                raise ValueError("No access_token in response")

            return tokens

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to exchange authorization code: {e}")

    def fetch_events(
        self,
        credentials: Dict[str, Any],
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch Gmail messages since last sync.

        Args:
            credentials: Dictionary containing access_token and refresh_token
            since: Only fetch messages after this timestamp
            filters: Optional filters (labels, max_results)

        Returns:
            List of Gmail message dictionaries

        Raises:
            ValueError: If API request fails
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("No access_token in credentials")

        # Build query
        query_parts = []
        if since:
            # Gmail uses Unix timestamp for after: query
            timestamp = int(since.timestamp())
            query_parts.append(f"after:{timestamp}")

        # Apply label filters if specified
        if filters and "labels" in filters:
            labels = filters["labels"]
            if isinstance(labels, str):
                labels = [labels]
            for label in labels:
                query_parts.append(f"label:{label}")

        query = " ".join(query_parts) if query_parts else None

        # Determine max results
        max_results = 100  # Default
        if filters and "max_results" in filters:
            max_results = min(filters["max_results"], 500)  # Cap at 500

        messages = []
        page_token = None

        # Fetch message list with pagination
        while True:
            list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {"maxResults": min(max_results - len(messages), 100)}

            if query:
                params["q"] = query
            if page_token:
                params["pageToken"] = page_token

            headers = {"Authorization": f"Bearer {access_token}"}

            try:
                response = requests.get(list_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                message_list = data.get("messages", [])

                # Fetch full message details for each message
                for msg_ref in message_list:
                    msg_id = msg_ref["id"]
                    msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                    msg_params = {"format": "full"}

                    msg_response = requests.get(
                        msg_url, headers=headers, params=msg_params, timeout=30
                    )
                    msg_response.raise_for_status()
                    full_message = msg_response.json()
                    messages.append(full_message)

                    # Check if we've reached max_results
                    if len(messages) >= max_results:
                        break

                # Check for more pages
                page_token = data.get("nextPageToken")
                if not page_token or len(messages) >= max_results:
                    break

            except requests.exceptions.RequestException as e:
                raise ValueError(f"Failed to fetch Gmail messages: {e}")

        return messages

    def transform_event(self, raw_event: Dict[str, Any]) -> EventPayload:
        """
        Transform Gmail message to TVOS EventPayload.

        Args:
            raw_event: Gmail message dictionary from API

        Returns:
            EventPayload protobuf message

        Raises:
            ValueError: If required fields are missing
        """
        # Extract message ID
        msg_id = raw_event.get("id")
        if not msg_id:
            raise ValueError("Gmail message missing 'id' field")

        # Extract timestamp (internalDate is in milliseconds)
        timestamp_ms = int(raw_event.get("internalDate", 0))
        if timestamp_ms == 0:
            # Fallback to current time if missing
            timestamp_ms = int(datetime.now().timestamp() * 1000)

        # Extract headers
        headers = {}
        payload = raw_event.get("payload", {})
        for header in payload.get("headers", []):
            name = header.get("name", "").lower()
            value = header.get("value", "")
            headers[name] = value

        # Extract key fields
        subject = headers.get("subject", "(No Subject)")
        from_addr = headers.get("from", "")
        to_addr = headers.get("to", "")
        date_str = headers.get("date", "")

        # Extract body
        body = self._extract_body(payload)

        # Build text payload
        text_payload = f"Subject: {subject}\n"
        if from_addr:
            text_payload += f"From: {from_addr}\n"
        if to_addr:
            text_payload += f"To: {to_addr}\n"
        text_payload += f"\n{body}"

        # Extract labels
        labels = raw_event.get("labelIds", [])

        # Build metadata
        metadata = {
            "connector": "gmail",
            "external_id": msg_id,
            "from": from_addr,
            "to": to_addr,
            "subject": subject,
            "date": date_str,
            "labels": json.dumps(labels),
            "thread_id": raw_event.get("threadId", ""),
        }

        # Create EventPayload
        event = EventPayload()
        event.event_id = f"gmail_{msg_id}"
        event.timestamp_ms = timestamp_ms
        event.source = "gmail"
        event.text_payload = text_payload

        # Add metadata
        for key, value in metadata.items():
            event.metadata[key] = str(value)

        return event

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body from Gmail message payload.

        Args:
            payload: Gmail message payload

        Returns:
            Email body text
        """
        # Try to get plain text body
        body = ""

        # Check if body is directly in payload
        if "body" in payload and "data" in payload["body"]:
            body_data = payload["body"]["data"]
            body = self._decode_body(body_data)
            return body

        # Check parts for multipart messages
        if "parts" in payload:
            body = self._extract_body_from_parts(payload["parts"])

        return body if body else "(No body content)"

    def _extract_body_from_parts(self, parts: List[Dict[str, Any]]) -> str:
        """
        Recursively extract body from message parts.

        Args:
            parts: List of message parts

        Returns:
            Extracted body text
        """
        for part in parts:
            mime_type = part.get("mimeType", "")

            # Prefer text/plain
            if mime_type == "text/plain":
                if "body" in part and "data" in part["body"]:
                    return self._decode_body(part["body"]["data"])

            # Recurse into nested parts
            if "parts" in part:
                body = self._extract_body_from_parts(part["parts"])
                if body:
                    return body

        # Fallback to text/html if no text/plain found
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/html":
                if "body" in part and "data" in part["body"]:
                    return self._decode_body(part["body"]["data"])

        return ""

    def _decode_body(self, data: str) -> str:
        """
        Decode base64url-encoded body data.

        Args:
            data: Base64url-encoded string

        Returns:
            Decoded text
        """
        try:
            # Gmail uses base64url encoding (RFC 4648)
            # Replace URL-safe characters and add padding
            data = data.replace("-", "+").replace("_", "/")
            # Add padding if needed
            padding = 4 - (len(data) % 4)
            if padding != 4:
                data += "=" * padding

            decoded = base64.b64decode(data)
            return decoded.decode("utf-8", errors="ignore")
        except Exception:
            return "(Unable to decode body)"

    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate Gmail credentials by making a test API call.

        Args:
            credentials: Credentials dictionary

        Returns:
            True if credentials are valid, False otherwise
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return False

        # Test with a simple profile request
        url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def get_rate_limit_info(self) -> Dict[str, int]:
        """
        Return Gmail API rate limit information.

        Returns:
            Dictionary with rate limit details
        """
        # Gmail API quotas (as of 2024)
        return {
            "requests_per_second": 250,
            "requests_per_day": 1_000_000_000,  # 1 billion per day
        }


class GitHubConnector(ConnectorBase):
    """
    GitHub integration using OAuth or Personal Access Token.
    Fetches repository events (commits, PRs, issues) and transforms them into TVOS events.
    """

    # OAuth configuration
    OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_BASE = "https://api.github.com"
    SCOPES = ["repo", "read:user"]
    REDIRECT_URI = "http://localhost:8000/connectors/github/callback"

    @property
    def name(self) -> str:
        """Unique connector identifier"""
        return "github"

    @property
    def display_name(self) -> str:
        """Human-readable name"""
        return "GitHub"

    def __init__(self):
        """Initialize GitHub connector with OAuth credentials from config"""
        self.client_id = Config.GITHUB_CLIENT_ID
        self.client_secret = Config.GITHUB_CLIENT_SECRET

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "GitHub OAuth credentials not configured. "
                "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables."
            )

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for GitHub.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            OAuth authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.REDIRECT_URI,
            "scope": " ".join(self.SCOPES),
        }

        if state:
            params["state"] = state

        return f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        GitHub OAuth also supports Personal Access Token authentication.

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary containing access_token and token_type

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": self.REDIRECT_URI,
        }

        headers = {
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                self.OAUTH_TOKEN_URL, 
                data=data, 
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            token_data = response.json()

            # Check for error in response
            if "error" in token_data:
                raise ValueError(
                    f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}"
                )

            # Validate required fields
            if "access_token" not in token_data:
                raise ValueError("Token response missing access_token")

            return token_data

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to exchange authorization code: {e}")

    def fetch_events(
        self,
        credentials: Dict[str, Any],
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch GitHub repository events (commits, PRs, issues) since last sync.

        Args:
            credentials: Dictionary containing access_token
            since: Only fetch events after this timestamp
            filters: Optional filters (repositories, event_types, max_results)

        Returns:
            List of GitHub event dictionaries

        Raises:
            ValueError: If API request fails
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("No access_token in credentials")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Determine max results
        max_results = 100  # Default
        if filters and "max_results" in filters:
            max_results = min(filters["max_results"], 1000)  # Cap at 1000

        # Get list of repositories to monitor
        repositories = []
        if filters and "repositories" in filters:
            # User specified repositories
            repos = filters["repositories"]
            if isinstance(repos, str):
                repositories = [repos]
            else:
                repositories = list(repos)
        else:
            # Fetch user's repositories
            repositories = self._fetch_user_repositories(headers, max_repos=10)

        # Determine which event types to fetch
        event_types = ["commits", "pulls", "issues"]
        if filters and "event_types" in filters:
            event_types = filters["event_types"]
            if isinstance(event_types, str):
                event_types = [event_types]

        # Fetch events from each repository
        all_events = []
        
        for repo in repositories:
            # Parse owner/repo format
            if "/" not in repo:
                continue  # Skip invalid repo format
            
            owner, repo_name = repo.split("/", 1)

            # Fetch different event types
            if "commits" in event_types:
                commits = self._fetch_commits(headers, owner, repo_name, since, max_results)
                all_events.extend(commits)

            if "pulls" in event_types:
                pulls = self._fetch_pull_requests(headers, owner, repo_name, since, max_results)
                all_events.extend(pulls)

            if "issues" in event_types:
                issues = self._fetch_issues(headers, owner, repo_name, since, max_results)
                all_events.extend(issues)

            # Stop if we've reached max_results
            if len(all_events) >= max_results:
                break

        # Sort by timestamp (most recent first) and limit
        all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return all_events[:max_results]

    def _fetch_user_repositories(
        self, 
        headers: Dict[str, str], 
        max_repos: int = 10
    ) -> List[str]:
        """
        Fetch user's repositories.

        Args:
            headers: Request headers with authorization
            max_repos: Maximum number of repositories to return

        Returns:
            List of repository names in "owner/repo" format
        """
        url = f"{self.GITHUB_API_BASE}/user/repos"
        params = {
            "sort": "updated",
            "per_page": max_repos,
            "affiliation": "owner,collaborator",
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            repos = response.json()

            return [repo["full_name"] for repo in repos]

        except requests.exceptions.RequestException:
            # If we can't fetch repos, return empty list
            return []

    def _fetch_commits(
        self,
        headers: Dict[str, str],
        owner: str,
        repo: str,
        since: Optional[datetime],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch commits from a repository using cursor-based pagination.

        Args:
            headers: Request headers with authorization
            owner: Repository owner
            repo: Repository name
            since: Only fetch commits after this timestamp
            max_results: Maximum number of commits to fetch

        Returns:
            List of commit event dictionaries
        """
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
        params = {
            "per_page": min(max_results, 100),  # GitHub max is 100 per page
        }

        if since:
            # GitHub uses ISO 8601 format
            params["since"] = since.isoformat()

        commits = []
        page = 1

        try:
            while len(commits) < max_results:
                params["page"] = page
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Check rate limit
                self._check_rate_limit(response)
                
                response.raise_for_status()
                page_commits = response.json()

                if not page_commits:
                    break

                # Transform commits to event format
                for commit in page_commits:
                    commits.append({
                        "type": "commit",
                        "repository": f"{owner}/{repo}",
                        "sha": commit["sha"],
                        "message": commit["commit"]["message"],
                        "author": commit["commit"]["author"]["name"],
                        "author_email": commit["commit"]["author"]["email"],
                        "timestamp": commit["commit"]["author"]["date"],
                        "url": commit["html_url"],
                        "raw": commit,
                    })

                # Check if there are more pages (Link header)
                if "Link" not in response.headers or 'rel="next"' not in response.headers["Link"]:
                    break

                page += 1

        except requests.exceptions.RequestException as e:
            # Log error but don't fail entire sync
            print(f"Error fetching commits from {owner}/{repo}: {e}")

        return commits

    def _fetch_pull_requests(
        self,
        headers: Dict[str, str],
        owner: str,
        repo: str,
        since: Optional[datetime],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch pull requests from a repository.

        Args:
            headers: Request headers with authorization
            owner: Repository owner
            repo: Repository name
            since: Only fetch PRs updated after this timestamp
            max_results: Maximum number of PRs to fetch

        Returns:
            List of PR event dictionaries
        """
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
        params = {
            "state": "all",  # Include open and closed PRs
            "sort": "updated",
            "direction": "desc",
            "per_page": min(max_results, 100),
        }

        pulls = []
        page = 1

        try:
            while len(pulls) < max_results:
                params["page"] = page
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Check rate limit
                self._check_rate_limit(response)
                
                response.raise_for_status()
                page_pulls = response.json()

                if not page_pulls:
                    break

                # Filter by timestamp if provided
                for pr in page_pulls:
                    updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
                    
                    if since and updated_at <= since:
                        # PRs are sorted by updated_at desc, so we can stop here
                        return pulls

                    pulls.append({
                        "type": "pull_request",
                        "repository": f"{owner}/{repo}",
                        "number": pr["number"],
                        "title": pr["title"],
                        "state": pr["state"],
                        "author": pr["user"]["login"],
                        "timestamp": pr["updated_at"],
                        "created_at": pr["created_at"],
                        "url": pr["html_url"],
                        "body": pr.get("body", ""),
                        "raw": pr,
                    })

                # Check if there are more pages
                if "Link" not in response.headers or 'rel="next"' not in response.headers["Link"]:
                    break

                page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error fetching pull requests from {owner}/{repo}: {e}")

        return pulls

    def _fetch_issues(
        self,
        headers: Dict[str, str],
        owner: str,
        repo: str,
        since: Optional[datetime],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch issues from a repository.

        Args:
            headers: Request headers with authorization
            owner: Repository owner
            repo: Repository name
            since: Only fetch issues updated after this timestamp
            max_results: Maximum number of issues to fetch

        Returns:
            List of issue event dictionaries
        """
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": min(max_results, 100),
        }

        if since:
            params["since"] = since.isoformat()

        issues = []
        page = 1

        try:
            while len(issues) < max_results:
                params["page"] = page
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Check rate limit
                self._check_rate_limit(response)
                
                response.raise_for_status()
                page_issues = response.json()

                if not page_issues:
                    break

                # Filter out pull requests (GitHub API returns PRs as issues)
                for issue in page_issues:
                    if "pull_request" in issue:
                        continue  # Skip PRs

                    issues.append({
                        "type": "issue",
                        "repository": f"{owner}/{repo}",
                        "number": issue["number"],
                        "title": issue["title"],
                        "state": issue["state"],
                        "author": issue["user"]["login"],
                        "timestamp": issue["updated_at"],
                        "created_at": issue["created_at"],
                        "url": issue["html_url"],
                        "body": issue.get("body", ""),
                        "labels": [label["name"] for label in issue.get("labels", [])],
                        "raw": issue,
                    })

                # Check if there are more pages
                if "Link" not in response.headers or 'rel="next"' not in response.headers["Link"]:
                    break

                page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error fetching issues from {owner}/{repo}: {e}")

        return issues

    def _check_rate_limit(self, response: requests.Response) -> None:
        """
        Check GitHub rate limit headers and raise exception if limit exceeded.

        Args:
            response: Response object from GitHub API

        Raises:
            ValueError: If rate limit is exceeded
        """
        if response.status_code == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                raise ValueError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            else:
                raise ValueError("Rate limit exceeded")

        # Check rate limit headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining and int(remaining) == 0:
            reset_time = response.headers.get("X-RateLimit-Reset")
            if reset_time:
                reset_dt = datetime.fromtimestamp(int(reset_time))
                raise ValueError(f"Rate limit exceeded. Resets at {reset_dt}")

    def handle_rate_limit(self, retry_after: Optional[int] = None) -> int:
        """
        Calculate backoff delay for rate limiting with exponential backoff.

        Args:
            retry_after: Suggested retry delay from API (seconds)

        Returns:
            Delay in seconds before next retry
        """
        if retry_after:
            return retry_after
        
        # Default exponential backoff for GitHub: start with 60 seconds
        return 60

    def get_rate_limit_status(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current rate limit status from GitHub API.

        Args:
            credentials: Dictionary containing access_token

        Returns:
            Dictionary with rate limit information

        Raises:
            ValueError: If API request fails
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("No access_token in credentials")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"{self.GITHUB_API_BASE}/rate_limit"

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract core rate limit info
            core = data.get("resources", {}).get("core", {})
            
            return {
                "limit": core.get("limit", 0),
                "remaining": core.get("remaining", 0),
                "reset": core.get("reset", 0),
                "reset_datetime": datetime.fromtimestamp(core.get("reset", 0)) if core.get("reset") else None,
            }

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch rate limit status: {e}")

    def get_rate_limit_info(self) -> Dict[str, int]:
        """
        Return GitHub API rate limit information.

        Returns:
            Dictionary with rate limit details
        """
        # GitHub API rate limits (as of 2024)
        # Authenticated requests: 5000 per hour
        # Unauthenticated: 60 per hour
        return {
            "requests_per_hour": 5000,
            "requests_per_hour_unauthenticated": 60,
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate GitHub credentials by making a test API call.

        Args:
            credentials: Credentials dictionary

        Returns:
            True if credentials are valid, False otherwise
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Test with a simple user request
        url = f"{self.GITHUB_API_BASE}/user"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def transform_event(self, raw_event: Dict[str, Any]) -> EventPayload:
        """
        Transform GitHub event (commit, PR, issue) to TVOS EventPayload.

        Args:
            raw_event: GitHub event dictionary from fetch_events

        Returns:
            EventPayload protobuf message

        Raises:
            ValueError: If required fields are missing
        """
        event_type = raw_event.get("type")
        if not event_type:
            raise ValueError("GitHub event missing 'type' field")

        repository = raw_event.get("repository", "")
        timestamp_str = raw_event.get("timestamp", "")

        # Parse timestamp
        try:
            if timestamp_str:
                # GitHub uses ISO 8601 format
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp_ms = int(dt.timestamp() * 1000)
            else:
                timestamp_ms = int(datetime.now().timestamp() * 1000)
        except Exception:
            timestamp_ms = int(datetime.now().timestamp() * 1000)

        # Transform based on event type
        if event_type == "commit":
            return self._transform_commit(raw_event, repository, timestamp_ms)
        elif event_type == "pull_request":
            return self._transform_pull_request(raw_event, repository, timestamp_ms)
        elif event_type == "issue":
            return self._transform_issue(raw_event, repository, timestamp_ms)
        else:
            raise ValueError(f"Unknown GitHub event type: {event_type}")

    def _transform_commit(
        self, 
        raw_event: Dict[str, Any], 
        repository: str, 
        timestamp_ms: int
    ) -> EventPayload:
        """
        Transform a commit event to EventPayload.

        Args:
            raw_event: Commit event dictionary
            repository: Repository name
            timestamp_ms: Timestamp in milliseconds

        Returns:
            EventPayload protobuf message
        """
        sha = raw_event.get("sha", "")
        message = raw_event.get("message", "")
        author = raw_event.get("author", "")
        author_email = raw_event.get("author_email", "")
        url = raw_event.get("url", "")

        # Create text payload
        text_payload = f"Commit to {repository}\n"
        text_payload += f"Author: {author}\n"
        text_payload += f"SHA: {sha[:8]}\n\n"
        text_payload += message

        # Create EventPayload
        event = EventPayload()
        event.event_id = f"github_commit_{sha}"
        event.timestamp_ms = timestamp_ms
        event.source = "github"
        event.text_payload = text_payload

        # Add metadata
        event.metadata["connector"] = "github"
        event.metadata["external_id"] = sha
        event.metadata["type"] = "commit"
        event.metadata["repository"] = repository
        event.metadata["author"] = author
        event.metadata["author_email"] = author_email
        event.metadata["url"] = url
        event.metadata["sha"] = sha

        return event

    def _transform_pull_request(
        self, 
        raw_event: Dict[str, Any], 
        repository: str, 
        timestamp_ms: int
    ) -> EventPayload:
        """
        Transform a pull request event to EventPayload.

        Args:
            raw_event: PR event dictionary
            repository: Repository name
            timestamp_ms: Timestamp in milliseconds

        Returns:
            EventPayload protobuf message
        """
        number = raw_event.get("number", 0)
        title = raw_event.get("title", "")
        state = raw_event.get("state", "")
        author = raw_event.get("author", "")
        body = raw_event.get("body", "")
        url = raw_event.get("url", "")
        created_at = raw_event.get("created_at", "")

        # Create text payload
        text_payload = f"Pull Request #{number} in {repository}\n"
        text_payload += f"Title: {title}\n"
        text_payload += f"Author: {author}\n"
        text_payload += f"State: {state}\n\n"
        if body:
            text_payload += body

        # Create EventPayload
        event = EventPayload()
        event.event_id = f"github_pr_{repository.replace('/', '_')}_{number}"
        event.timestamp_ms = timestamp_ms
        event.source = "github"
        event.text_payload = text_payload

        # Add metadata
        event.metadata["connector"] = "github"
        event.metadata["external_id"] = f"pr_{number}"
        event.metadata["type"] = "pull_request"
        event.metadata["repository"] = repository
        event.metadata["author"] = author
        event.metadata["number"] = str(number)
        event.metadata["state"] = state
        event.metadata["url"] = url
        event.metadata["created_at"] = created_at

        return event

    def _transform_issue(
        self, 
        raw_event: Dict[str, Any], 
        repository: str, 
        timestamp_ms: int
    ) -> EventPayload:
        """
        Transform an issue event to EventPayload.

        Args:
            raw_event: Issue event dictionary
            repository: Repository name
            timestamp_ms: Timestamp in milliseconds

        Returns:
            EventPayload protobuf message
        """
        number = raw_event.get("number", 0)
        title = raw_event.get("title", "")
        state = raw_event.get("state", "")
        author = raw_event.get("author", "")
        body = raw_event.get("body", "")
        url = raw_event.get("url", "")
        labels = raw_event.get("labels", [])
        created_at = raw_event.get("created_at", "")

        # Create text payload
        text_payload = f"Issue #{number} in {repository}\n"
        text_payload += f"Title: {title}\n"
        text_payload += f"Author: {author}\n"
        text_payload += f"State: {state}\n"
        if labels:
            text_payload += f"Labels: {', '.join(labels)}\n"
        text_payload += "\n"
        if body:
            text_payload += body

        # Create EventPayload
        event = EventPayload()
        event.event_id = f"github_issue_{repository.replace('/', '_')}_{number}"
        event.timestamp_ms = timestamp_ms
        event.source = "github"
        event.text_payload = text_payload

        # Add metadata
        event.metadata["connector"] = "github"
        event.metadata["external_id"] = f"issue_{number}"
        event.metadata["type"] = "issue"
        event.metadata["repository"] = repository
        event.metadata["author"] = author
        event.metadata["number"] = str(number)
        event.metadata["state"] = state
        event.metadata["url"] = url
        event.metadata["labels"] = json.dumps(labels)
        event.metadata["created_at"] = created_at

        return event
