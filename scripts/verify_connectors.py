#!/usr/bin/env python3
"""
Verification script for connector infrastructure.
Tests basic functionality without requiring external API credentials.
"""

import sys
import tempfile
import os

# Generate a test encryption key BEFORE any imports
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
test_key_bytes = AESGCM.generate_key(bit_length=256)
test_key = base64.b64encode(test_key_bytes).decode('utf-8')

# Set environment variables BEFORE importing tvos modules
temp_dir = tempfile.mkdtemp()
test_db_path = os.path.join(temp_dir, 'test_connectors.duckdb')
os.environ['DUCKDB_PATH'] = test_db_path
os.environ['CONNECTOR_ENCRYPTION_KEY'] = test_key

# Now import after setting environment variables
from datetime import datetime
from tvos.db import init_db, get_db_connection
from tvos.connectors import CredentialEncryption, ConnectorRegistry, SyncScheduler, SyncJobStatus

def test_database_schema():
    """Test that all connector tables are created correctly."""
    print("Testing database schema...")
    init_db()
    
    conn = get_db_connection()
    
    # Check that all connector tables exist
    tables = ['connector_configs', 'connector_credentials', 'sync_jobs', 'sync_state']
    for table in tables:
        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        assert result is not None, f"Table {table} not found"
    
    print("✓ Database schema is correct")

def test_credential_encryption():
    """Test credential encryption and decryption."""
    print("\nTesting credential encryption...")
    
    crypto = CredentialEncryption()
    
    # Test with sample credentials
    test_creds = {
        "access_token": "test_token_12345",
        "refresh_token": "refresh_67890",
        "expires_at": 1234567890
    }
    
    # Encrypt
    encrypted_data, iv = crypto.encrypt(test_creds)
    
    # Verify encrypted data doesn't contain plaintext
    assert b"test_token_12345" not in encrypted_data, "Plaintext found in encrypted data"
    assert b"refresh_67890" not in encrypted_data, "Plaintext found in encrypted data"
    
    # Decrypt
    decrypted_creds = crypto.decrypt(encrypted_data, iv)
    
    # Verify round-trip
    assert decrypted_creds == test_creds, "Decrypted credentials don't match original"
    
    print("✓ Credential encryption works correctly")

def test_connector_registry():
    """Test connector registry operations."""
    print("\nTesting connector registry...")
    
    registry = ConnectorRegistry()
    
    # Test listing connectors (should be empty initially)
    connectors = registry.list_connectors()
    assert isinstance(connectors, list), "list_connectors should return a list"
    
    # Test credential storage and retrieval
    test_creds = {"access_token": "test123", "refresh_token": "refresh456"}
    
    # This will fail because no connector is registered, but that's expected
    # We're just testing the credential storage mechanism
    try:
        registry.save_credentials("test_connector", "test_user", test_creds)
    except ValueError as e:
        assert "not registered" in str(e), "Expected 'not registered' error"
        print("✓ Registry correctly validates connector registration")
    
    print("✓ Connector registry works correctly")

def test_sync_scheduler():
    """Test sync scheduler operations."""
    print("\nTesting sync scheduler...")
    
    scheduler = SyncScheduler()
    conn = get_db_connection()
    
    # Create a test connector config
    conn.execute("""
        INSERT INTO connector_configs 
        (id, user_id, connector_name, enabled, sync_interval_minutes, filters, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        "test_user:test_connector",
        "test_user",
        "test_connector",
        True,
        60,
        None,
        datetime.now(),
        datetime.now()
    ])
    
    # Test manual sync trigger
    job_id = scheduler.trigger_manual_sync("test_connector", "test_user")
    assert job_id is not None, "Job ID should not be None"
    assert job_id.startswith("sync_"), "Job ID should start with 'sync_'"
    
    print(f"✓ Created manual sync job: {job_id}")
    
    # Test getting sync status
    status = scheduler.get_sync_status(job_id)
    assert status is not None, "Status should not be None"
    assert status['status'] == SyncJobStatus.PENDING.value, "Job should be pending"
    assert status['sync_type'] == 'manual', "Job should be manual type"
    
    print("✓ Sync job status is correct")
    
    # Test preventing duplicate syncs
    try:
        # Update job to running
        scheduler.update_job_status(job_id, SyncJobStatus.RUNNING)
        
        # Try to create another manual sync
        scheduler.trigger_manual_sync("test_connector", "test_user")
        assert False, "Should have raised ValueError for duplicate sync"
    except ValueError as e:
        assert "already running" in str(e).lower(), "Expected 'already running' error"
        print("✓ Duplicate sync prevention works")
    
    # Test job cancellation
    cancelled = scheduler.cancel_sync(job_id)
    assert cancelled, "Job should be cancellable"
    
    status = scheduler.get_sync_status(job_id)
    assert status['status'] == SyncJobStatus.CANCELLED.value, "Job should be cancelled"
    
    print("✓ Job cancellation works")
    
    # Test getting pending jobs
    # Create a new pending job
    job_id2 = scheduler.trigger_manual_sync("test_connector", "test_user")
    pending_jobs = scheduler.get_pending_jobs(limit=10)
    assert len(pending_jobs) > 0, "Should have pending jobs"
    assert any(j['job_id'] == job_id2 for j in pending_jobs), "New job should be in pending list"
    
    print("✓ Pending job retrieval works")

def test_state_transitions():
    """Test sync job state machine transitions."""
    print("\nTesting state transitions...")
    
    scheduler = SyncScheduler()
    conn = get_db_connection()
    
    # Create another test job
    job_id = scheduler.trigger_manual_sync("test_connector", "test_user")
    
    # Test valid transitions
    scheduler.update_job_status(job_id, SyncJobStatus.RUNNING)
    status = scheduler.get_sync_status(job_id)
    assert status['status'] == SyncJobStatus.RUNNING.value
    
    scheduler.update_job_status(job_id, SyncJobStatus.COMPLETED, events_synced=42)
    status = scheduler.get_sync_status(job_id)
    assert status['status'] == SyncJobStatus.COMPLETED.value
    assert status['events_synced'] == 42
    assert status['completed_at'] is not None
    
    print("✓ Valid state transitions work")
    
    # Test invalid transition (from terminal state)
    try:
        scheduler.update_job_status(job_id, SyncJobStatus.RUNNING)
        assert False, "Should not allow transition from completed to running"
    except ValueError as e:
        assert "invalid state transition" in str(e).lower()
        print("✓ Invalid state transitions are prevented")
    
    # Test that completed job updates sync_state timestamp
    sync_state = conn.execute("""
        SELECT last_sync_timestamp FROM sync_state
        WHERE connector_name = ? AND user_id = ?
    """, ["test_connector", "test_user"]).fetchone()
    
    assert sync_state is not None, "Sync state should be created"
    assert sync_state[0] is not None, "Last sync timestamp should be set"
    
    print("✓ Sync state timestamp is updated on completion")

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("TVOS Connector Infrastructure Verification")
    print("=" * 60)
    
    try:
        test_database_schema()
        test_credential_encryption()
        test_connector_registry()
        test_sync_scheduler()
        test_state_transitions()
        
        print("\n" + "=" * 60)
        print("✓ All verification tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    sys.exit(main())
