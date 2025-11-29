# Implementation Plan

- [x] 1. Set up connector infrastructure and database schema
  - [x] 1.1 Create database schema for connector tables
    - Add connector_configs, connector_credentials, sync_jobs, and sync_state tables to db.py
    - Create indexes for performance optimization
    - _Requirements: 5.1, 6.1_
  
  - [x] 1.2 Implement credential encryption utility
    - Create CredentialEncryption class with AES-256-GCM encryption
    - Implement encrypt() and decrypt() methods
    - Store encryption key in environment configuration
    - _Requirements: 1.2, 6.1_
  
  - [ ]* 1.3 Write property test for credential encryption
    - **Property 2: Credential encryption round-trip**
    - **Validates: Requirements 1.2, 2.2, 6.1, 6.3**
  
  - [x] 1.4 Create base connector interface
    - Define ConnectorBase abstract class with required methods
    - Implement get_auth_url, authenticate, fetch_events, transform_event
    - Add validation and rate limit helper methods
    - _Requirements: 5.1, 5.2_

- [x] 2. Implement connector registry and lifecycle management
  - [x] 2.1 Create ConnectorRegistry class
    - Implement connector registration and retrieval
    - Add credential storage/retrieval with encryption
    - Implement list_connectors with status information
    - _Requirements: 5.2, 6.1_
  
  - [ ]* 2.2 Write property test for configuration persistence
    - **Property 17: Configuration persistence round-trip**
    - **Validates: Requirements 7.3**
  
  - [x] 2.3 Implement connector status tracking
    - Add methods to query connector status with all required fields
    - Track last sync timestamp, event count, enabled state
    - _Requirements: 3.2_
  
  - [ ]* 2.4 Write property test for connector status
    - **Property 8: Connector status includes required fields**
    - **Validates: Requirements 3.2**
  
  - [x] 2.5 Implement disconnect functionality
    - Add disconnect method that removes credentials and disables connector
    - _Requirements: 3.4_
  
  - [ ]* 2.6 Write property test for disconnect
    - **Property 9: Disconnect removes credentials**
    - **Validates: Requirements 3.4**

- [x] 3. Build sync scheduler and job management
  - [x] 3.1 Create SyncScheduler class
    - Implement schedule_sync for periodic jobs
    - Implement trigger_manual_sync for immediate execution
    - Add job status tracking and cancellation
    - _Requirements: 1.5, 4.1, 4.5_
  
  - [x] 3.2 Implement sync job state machine
    - Define job states: pending, running, completed, failed, cancelled
    - Implement state transitions with validation
    - Track job metadata (started_at, completed_at, events_synced, error_message)
    - _Requirements: 4.3, 4.4_
  
  - [ ]* 3.3 Write property test for manual sync job creation
    - **Property 11: Manual sync creates job**
    - **Validates: Requirements 4.1**
  
  - [ ]* 3.4 Write property test for concurrent sync prevention
    - **Property 12: Concurrent sync prevention**
    - **Validates: Requirements 4.2**
  
  - [ ]* 3.5 Write property test for sync completion
    - **Property 13: Sync completion updates timestamp**
    - **Validates: Requirements 4.3**
  
  - [ ]* 3.6 Write property test for sync cancellation
    - **Property 15: Running sync is cancellable**
    - **Validates: Requirements 4.5**

- [x] 4. Implement sync worker thread
  - [x] 4.1 Create run_sync_worker function
    - Set up background thread similar to ingest/embed workers
    - Poll for scheduled and manual sync jobs
    - Execute sync jobs with error handling
    - _Requirements: 1.5, 4.1_
  
  - [x] 4.2 Implement sync execution logic
    - Fetch credentials for connector
    - Call connector.fetch_events with last sync timestamp
    - Transform and inject events into TVOS pipeline
    - Update sync state and job status
    - _Requirements: 1.3, 1.4_
  
  - [x] 4.3 Add error handling and retry logic
    - Catch and log connector exceptions
    - Implement exponential backoff for transient errors
    - Update job status on failure with error details
    - _Requirements: 5.5, 9.1, 9.3_
  
  - [ ]* 4.4 Write property test for exception isolation
    - **Property 16: Connector exception isolation**
    - **Validates: Requirements 5.5**
  
  - [ ]* 4.5 Write property test for sync failure recording
    - **Property 14: Sync failure records error**
    - **Validates: Requirements 4.4, 9.1**
  
  - [ ]* 4.6 Write property test for network retry backoff
    - **Property 23: Network error retry with backoff**
    - **Validates: Requirements 9.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Gmail connector
  - [x] 6.1 Create GmailConnector class
    - Implement OAuth flow with Google API
    - Add configuration for client_id and client_secret
    - Implement get_auth_url and authenticate methods
    - _Requirements: 1.1, 1.2_
  
  - [ ]* 6.2 Write property test for OAuth URL generation
    - **Property 1: OAuth flow returns valid authentication URL**
    - **Validates: Requirements 1.1, 2.1**
  
  - [x] 6.3 Implement Gmail event fetching
    - Use Gmail API to fetch messages since last sync
    - Support filtering by labels and date ranges
    - Implement pagination for large result sets
    - _Requirements: 1.3, 10.3_
  
  - [ ]* 6.4 Write property test for incremental sync
    - **Property 3: Incremental sync respects timestamps**
    - **Validates: Requirements 1.3, 2.3**
  
  - [x] 6.5 Implement Gmail event transformation
    - Extract subject, from, body, timestamp from Gmail message
    - Create EventPayload with source="gmail"
    - Add connector metadata (external_id, labels, etc.)
    - _Requirements: 1.4, 8.1_
  
  - [ ]* 6.6 Write property test for Gmail transformation
    - **Property 4: Gmail transformation completeness**
    - **Validates: Requirements 1.4**
  
  - [ ]* 6.7 Write property test for filter application
    - **Property 25: Filter application during sync**
    - **Validates: Requirements 10.3, 10.4**

- [x] 7. Implement GitHub connector
  - [x] 7.1 Create GitHubConnector class
    - Implement OAuth flow with GitHub API
    - Support personal access token authentication
    - Implement get_auth_url and authenticate methods
    - _Requirements: 2.1, 2.2_
  
  - [x] 7.2 Implement GitHub event fetching
    - Use GitHub API to fetch repository events (commits, PRs, issues)
    - Support filtering by repository and event type
    - Implement cursor-based pagination
    - _Requirements: 2.3, 10.3_
  
  - [x] 7.3 Implement rate limit handling
    - Check GitHub rate limit headers
    - Implement exponential backoff on 429 responses
    - Track and respect rate limit windows
    - _Requirements: 2.5_
  
  - [ ]* 7.4 Write property test for rate limit backoff
    - **Property 7: Rate limit backoff increases delays**
    - **Validates: Requirements 2.5**
  
  - [x] 7.5 Implement GitHub event transformation
    - Transform commits, PRs, issues to EventPayload
    - Extract relevant metadata (repo, author, action)
    - Create EventPayload with source="github"
    - _Requirements: 2.4, 8.1_
  
  - [ ]* 7.6 Write property test for GitHub transformation
    - **Property 5: GitHub transformation completeness**
    - **Validates: Requirements 2.4**

- [ ] 8. Create connector management API endpoints
  - [ ] 8.1 Add GET /connectors endpoint
    - List all available connectors with status
    - Include connection status, last sync, event count
    - _Requirements: 3.1, 3.2_
  
  - [ ] 8.2 Add GET /connectors/{name} endpoint
    - Return detailed connector configuration
    - Include sync history and error logs
    - _Requirements: 3.3_
  
  - [ ] 8.3 Add POST /connectors/{name}/auth endpoint
    - Initiate OAuth flow or accept credentials
    - Return auth URL or store credentials
    - _Requirements: 1.1, 2.1_
  
  - [ ] 8.4 Add POST /connectors/{name}/callback endpoint
    - Handle OAuth callback with authorization code
    - Exchange code for tokens and store encrypted
    - _Requirements: 1.2, 2.2_
  
  - [ ] 8.5 Add PUT /connectors/{name}/config endpoint
    - Update connector configuration (interval, filters, enabled)
    - Validate configuration before saving
    - _Requirements: 7.1, 10.3_
  
  - [ ]* 8.6 Write property test for filter updates preserving credentials
    - **Property 26: Filter updates preserve credentials**
    - **Validates: Requirements 10.5**
  
  - [ ] 8.7 Add DELETE /connectors/{name} endpoint
    - Disconnect connector and remove credentials
    - Cancel any running sync jobs
    - _Requirements: 3.4_
  
  - [ ] 8.8 Add POST /connectors/{name}/sync endpoint
    - Trigger manual sync for connector
    - Prevent duplicate concurrent syncs
    - Return job_id for status tracking
    - _Requirements: 4.1, 4.2_
  
  - [ ] 8.9 Add GET /connectors/{name}/sync/{job_id} endpoint
    - Return sync job status and progress
    - Include events_synced, error_message if failed
    - _Requirements: 3.5, 4.3, 4.4_
  
  - [ ]* 8.10 Write property test for sync progress queryability
    - **Property 10: Sync progress is queryable**
    - **Validates: Requirements 3.5**
  
  - [ ] 8.11 Add DELETE /connectors/{name}/sync/{job_id} endpoint
    - Cancel running sync job
    - Update job status to cancelled
    - _Requirements: 4.5_

- [ ] 9. Implement adaptive sync and failure handling
  - [ ] 9.1 Add authentication failure detection
    - Detect 401/403 responses from external APIs
    - Mark connector as requiring re-authentication
    - Disable auto-sync until re-authenticated
    - _Requirements: 9.2_
  
  - [ ]* 9.2 Write property test for auth failure handling
    - **Property 22: Authentication failure marks re-auth needed**
    - **Validates: Requirements 9.2**
  
  - [ ] 9.3 Implement rate limit adaptation
    - Track consecutive rate limit errors
    - Automatically increase sync interval when limits hit
    - Reset interval when syncs succeed
    - _Requirements: 7.4_
  
  - [ ]* 9.4 Write property test for rate limit adaptation
    - **Property 18: Rate limit adaptation**
    - **Validates: Requirements 7.4**
  
  - [ ] 9.5 Implement failure threshold logic
    - Track consecutive sync failures per connector
    - Disable auto-sync after N failures (N=5)
    - Log and notify user of disabled connector
    - _Requirements: 9.4_
  
  - [ ]* 9.6 Write property test for repeated failure handling
    - **Property 24: Repeated failure disables auto-sync**
    - **Validates: Requirements 9.4**
  
  - [ ] 9.7 Implement sync interval scheduling
    - Schedule jobs based on configured interval
    - Support manual, 15min, 1hr, 6hr, 24hr intervals
    - Persist schedule across restarts
    - _Requirements: 1.5, 7.1, 7.2_
  
  - [ ]* 9.8 Write property test for sync scheduling
    - **Property 6: Sync scheduling respects intervals**
    - **Validates: Requirements 1.5, 7.2**
  
  - [ ] 9.9 Implement enabled flag behavior
    - When enabled=false, stop scheduling new jobs
    - Preserve credentials when disabled
    - Allow re-enabling without re-authentication
    - _Requirements: 7.5_
  
  - [ ]* 9.10 Write property test for disabled sync behavior
    - **Property 19: Disabled sync stops scheduling**
    - **Validates: Requirements 7.5**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Extend event querying for connector sources
  - [ ] 11.1 Add source filtering to /query/window endpoint
    - Accept optional source parameter
    - Filter events by connector source
    - _Requirements: 8.2_
  
  - [ ]* 11.2 Write property test for source filtering
    - **Property 20: Source filtering accuracy**
    - **Validates: Requirements 8.2**
  
  - [ ] 11.3 Update analytics endpoints for source grouping
    - Modify drift analysis to support grouping by source
    - Update cluster analysis to include source metadata
    - _Requirements: 8.5_
  
  - [ ]* 11.4 Write property test for drift source grouping
    - **Property 21: Drift analysis supports source grouping**
    - **Validates: Requirements 8.5**

- [ ] 12. Build connector UI components
  - [ ] 12.1 Create ConnectorList component
    - Display all available connectors with status badges
    - Show connection status, last sync, event count
    - Add "Connect" button for disconnected connectors
    - _Requirements: 3.1, 3.2_
  
  - [ ] 12.2 Create ConnectorDetail component
    - Show detailed connector configuration
    - Display sync history and error logs
    - Provide manual sync button
    - Allow configuration editing (interval, filters)
    - _Requirements: 3.3, 4.1, 7.1_
  
  - [ ] 12.3 Create ConnectorSetup component
    - Display OAuth flow or credential input
    - Show data collection preview and privacy info
    - Allow filter configuration before connecting
    - _Requirements: 1.1, 2.1, 10.1, 10.3_
  
  - [ ] 12.4 Create SyncProgress component
    - Display real-time sync progress
    - Show events synced count and status
    - Provide cancel button for running syncs
    - _Requirements: 3.5, 4.5_
  
  - [ ] 12.5 Add connector source badges to EventStream
    - Visually distinguish external events
    - Show connector icon/badge on event cards
    - Add tooltip with connector metadata
    - _Requirements: 8.3_
  
  - [ ] 12.6 Integrate connector UI into main Dashboard
    - Add "Connectors" tab or section to Dashboard
    - Wire up API calls to connector endpoints
    - Handle OAuth callback routing
    - _Requirements: 3.1_

- [ ] 13. Add connector worker to application startup
  - [ ] 13.1 Start sync worker thread in api.py
    - Add run_sync_worker to startup_event
    - Initialize ConnectorRegistry on startup
    - Register Gmail and GitHub connectors
    - _Requirements: 1.5, 5.2_
  
  - [ ] 13.2 Add connector configuration to Config
    - Add Gmail OAuth credentials (client_id, client_secret)
    - Add GitHub OAuth credentials
    - Add encryption key configuration
    - _Requirements: 1.1, 2.1, 6.1_
  
  - [ ] 13.3 Update .env.example with connector variables
    - Document required environment variables
    - Provide example values for OAuth setup
    - _Requirements: 1.1, 2.1_

- [ ] 14. Documentation and Security Hardening
  - [ ] 14.1 Create API documentation for connectors
    - Document new endpoints in OpenAPI/FastAPI
    - Add examples for authentication flows
  - [ ] 14.2 Implement Security Headers
    - Ensure OAuth callbacks have proper security headers
    - Validate state parameters strictly
  - [ ] 14.3 Add User Guide for Connectors
    - Write documentation on how to set up Gmail/GitHub connectors
    - Explain data privacy and scope
  - [ ] 14.4 Conduct Security Review
    - Review credential encryption implementation
    - Verify token storage security

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
