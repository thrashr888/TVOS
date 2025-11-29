# GitHub Connector Implementation

## Overview

This document describes the implementation of the GitHub connector for TVOS, which enables integration with GitHub repositories to fetch and analyze commits, pull requests, and issues.

## Implementation Summary

### Task 7.1: Create GitHubConnector Class ✓

Implemented the `GitHubConnector` class in `tvos/connectors.py` with:

- **OAuth Configuration**: Support for GitHub OAuth 2.0 flow
- **Authentication Methods**: 
  - `get_auth_url()`: Generates OAuth authorization URL with proper scopes
  - `authenticate()`: Exchanges authorization code for access token
- **Configuration**: Uses `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` from environment

**Requirements Validated**: 2.1, 2.2

### Task 7.2: Implement GitHub Event Fetching ✓

Implemented comprehensive event fetching with:

- **Event Types Supported**:
  - Commits: Fetches commit history with author, message, and SHA
  - Pull Requests: Fetches PRs with title, state, author, and body
  - Issues: Fetches issues with labels, state, and body

- **Features**:
  - Cursor-based pagination for efficient data retrieval
  - Incremental sync using `since` timestamp parameter
  - Repository filtering (user-specified or auto-fetch user's repos)
  - Event type filtering (commits, pulls, issues)
  - Configurable max results with sensible defaults

- **Helper Methods**:
  - `_fetch_user_repositories()`: Auto-discovers user's repositories
  - `_fetch_commits()`: Fetches commits with pagination
  - `_fetch_pull_requests()`: Fetches PRs with timestamp filtering
  - `_fetch_issues()`: Fetches issues (excluding PRs)
  - `_check_rate_limit()`: Monitors rate limit headers

**Requirements Validated**: 2.3, 10.3

### Task 7.3: Implement Rate Limit Handling ✓

Implemented comprehensive rate limit handling:

- **Rate Limit Detection**:
  - Checks HTTP 429 status codes
  - Monitors `X-RateLimit-Remaining` header
  - Reads `X-RateLimit-Reset` timestamp

- **Exponential Backoff**:
  - `handle_rate_limit()`: Calculates retry delays
  - Respects `Retry-After` header when provided
  - Default 60-second backoff for GitHub

- **Rate Limit Status**:
  - `get_rate_limit_status()`: Queries current rate limit state
  - `get_rate_limit_info()`: Returns GitHub's rate limits (5000/hour authenticated)

- **Error Handling**:
  - Raises clear exceptions with reset times
  - Integrates with sync worker's retry logic

**Requirements Validated**: 2.5

### Task 7.5: Implement GitHub Event Transformation ✓

Implemented event transformation for all GitHub event types:

- **Main Transformation Method**:
  - `transform_event()`: Routes to type-specific transformers
  - Handles timestamp parsing (ISO 8601 format)
  - Creates EventPayload protobuf messages

- **Type-Specific Transformers**:
  - `_transform_commit()`: Converts commits to events
    - Includes: SHA, message, author, repository
    - Event ID format: `github_commit_{sha}`
  
  - `_transform_pull_request()`: Converts PRs to events
    - Includes: number, title, state, author, body
    - Event ID format: `github_pr_{owner}_{repo}_{number}`
  
  - `_transform_issue()`: Converts issues to events
    - Includes: number, title, state, author, labels, body
    - Event ID format: `github_issue_{owner}_{repo}_{number}`

- **Metadata Enrichment**:
  - All events tagged with `source="github"`
  - Connector metadata includes: type, repository, author, URL
  - Preserves external IDs for deduplication

**Requirements Validated**: 2.4, 8.1

## Testing

Created comprehensive test suite in `scripts/test_github_connector.py`:

- ✓ OAuth URL generation (Requirement 2.1)
- ✓ Connector properties (name, display_name)
- ✓ Rate limit information
- ✓ Event transformation for commits, PRs, and issues (Requirement 2.4)
- ✓ Rate limit handling with exponential backoff (Requirement 2.5)

All tests pass successfully.

## API Integration

The GitHub connector integrates with the existing TVOS connector infrastructure:

- **ConnectorBase Interface**: Fully implements all required methods
- **ConnectorRegistry**: Can be registered for use by sync worker
- **SyncScheduler**: Compatible with existing job scheduling
- **Event Pipeline**: Transformed events flow through standard TVOS ingestion

## Configuration

Required environment variables:

```bash
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

## Usage Example

```python
from tvos.connectors import GitHubConnector

# Initialize connector
connector = GitHubConnector()

# Get OAuth URL
auth_url = connector.get_auth_url(state="csrf_token")

# After user authorizes, exchange code for token
credentials = connector.authenticate(auth_code)

# Fetch events
events = connector.fetch_events(
    credentials=credentials,
    since=datetime(2024, 1, 1),
    filters={
        "repositories": ["owner/repo"],
        "event_types": ["commits", "pulls", "issues"],
        "max_results": 100
    }
)

# Transform events
for raw_event in events:
    event_payload = connector.transform_event(raw_event)
    # event_payload is ready for TVOS ingestion
```

## Next Steps

To complete the GitHub connector integration:

1. **Task 8**: Create API endpoints for connector management
2. **Task 13**: Register GitHub connector in application startup
3. **Task 12**: Build UI components for GitHub connector setup

## Files Modified

- `tvos/connectors.py`: Added `GitHubConnector` class (~400 lines)
- `scripts/test_github_connector.py`: Created test suite (~200 lines)
- `docs/github-connector-implementation.md`: This documentation

## Compliance

This implementation satisfies all requirements from the design document:

- ✓ Requirement 2.1: OAuth authentication flow
- ✓ Requirement 2.2: Secure credential storage (via ConnectorRegistry)
- ✓ Requirement 2.3: Incremental sync with timestamps
- ✓ Requirement 2.4: Event transformation with metadata
- ✓ Requirement 2.5: Rate limit handling with exponential backoff
- ✓ Requirement 8.1: Event tagging with source metadata
- ✓ Requirement 10.3: Repository and event type filtering
