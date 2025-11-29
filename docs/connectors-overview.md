# TVOS Connectors Overview

## What are Connectors?

Connectors extend TVOS's event ingestion capabilities to include data from third-party services like Gmail and GitHub. They allow you to analyze external data alongside your local system events using TVOS's temporal semantic analytics.

## Available Connectors

### Gmail
Ingest and analyze your email data for semantic patterns, trends, and insights.

**Use Cases:**
- Track communication patterns over time
- Identify semantic drift in email topics
- Search emails semantically (beyond keyword matching)
- Cluster emails by topic or sentiment
- Analyze response times and email volume

**Setup Guide:** [Gmail Connector Setup](./gmail-connector-setup.md)

### GitHub (Coming Soon)
Track repository activity including commits, pull requests, and issues.

**Use Cases:**
- Monitor code change patterns
- Analyze commit message semantics
- Track project velocity and activity
- Identify topic clusters in issues and PRs

## How Connectors Work

### Architecture

```
External Service (Gmail/GitHub)
         ↓
    OAuth Authentication
         ↓
   Connector Fetches Data
         ↓
  Transform to TVOS Events
         ↓
   Existing Ingest Pipeline
         ↓
  DuckDB + Weaviate Storage
         ↓
   Analytics & Visualization
```

### Data Flow

1. **Authentication**: Connectors use OAuth to securely access external services
2. **Sync Jobs**: Scheduled or manual jobs fetch new data since the last sync
3. **Transformation**: External data is converted to TVOS EventPayload format
4. **Ingestion**: Events flow through the same pipeline as local events
5. **Storage**: Events are stored in DuckDB with embeddings in Weaviate
6. **Analytics**: All TVOS analytics work seamlessly with external events

### Event Tagging

External events are tagged with metadata to distinguish them:

- **source**: Connector name (e.g., "gmail", "github")
- **connector**: Connector identifier
- **external_id**: Original ID from external service
- **sync_job_id**: ID of the sync job that fetched the event
- **connector_metadata**: Service-specific metadata

## Key Features

### Secure Credential Storage

- All credentials encrypted with AES-256-GCM
- Encryption keys stored separately from credentials
- Credentials never logged in plaintext
- Support for credential rotation

### Flexible Sync Scheduling

Choose sync frequency based on your needs:
- **Manual**: Sync only when you trigger it
- **15 minutes**: Near real-time updates
- **1 hour**: Balanced freshness and API usage
- **6 hours**: Periodic updates
- **24 hours**: Daily batch sync

### Smart Rate Limiting

- Automatic exponential backoff on rate limits
- Adaptive sync intervals when limits are hit
- Respects service provider quotas
- Circuit breaker for repeated failures

### Incremental Sync

- Only fetches new data since last sync
- Uses timestamps and cursors for efficiency
- Minimizes API calls and data transfer
- Preserves sync state across restarts

### Filtering & Configuration

- Filter by labels, repositories, or other criteria
- Limit results per sync to control volume
- Configure per-connector settings
- Update filters without re-authentication

## Managing Connectors

### Viewing Connector Status

The Connectors UI shows:
- Connection status (connected/disconnected)
- Last sync timestamp
- Next scheduled sync
- Total events synced
- Current configuration
- Error status and messages

### Manual Sync

Trigger an immediate sync for any connector:
1. Navigate to the connector details
2. Click "Sync Now"
3. Monitor progress in real-time
4. View results when complete

### Cancelling Sync

Stop a running sync job:
1. View the connector details during sync
2. Click "Cancel Sync"
3. Job status updates to "cancelled"

### Updating Configuration

Change sync settings without re-authenticating:
1. Open connector details
2. Modify sync interval or filters
3. Click "Save Configuration"
4. Changes apply to next sync

### Disconnecting

Remove a connector:
1. Navigate to connector details
2. Click "Disconnect"
3. Confirm the action

This removes credentials and stops syncing, but preserves existing data.

## Data Privacy & Security

### Local-First Architecture

- All data stored locally on your machine
- No data sent to TVOS servers (there are none!)
- External services only accessed via official APIs
- You control what data is synced

### OAuth Security

- Industry-standard OAuth 2.0 authentication
- Read-only access scopes
- Tokens stored encrypted
- Easy revocation via service provider

### Credential Encryption

- AES-256-GCM encryption at rest
- Unique initialization vectors per credential
- Keys managed via environment variables
- Secure key generation utilities

### Audit & Control

- View all connected services in one place
- Monitor sync activity and data volume
- Revoke access anytime
- Delete synced data independently

## Querying External Events

### Filter by Source

Query only events from a specific connector:

```sql
SELECT * FROM events WHERE source = 'gmail'
```

### Semantic Search

Search across all events including external sources:

```
POST /query/semantic
{
  "query": "project deadline discussion",
  "limit": 10
}
```

### Time Windows

Analyze external events in time windows:

```
GET /query/window?start=2024-01-01&end=2024-01-31&source=gmail
```

### Drift Analysis

Compare semantic drift across sources:

```
POST /analytics/drift
{
  "group_by": "source"
}
```

## Best Practices

### Sync Frequency

- **High-volume sources**: Use longer intervals (6-24 hours)
- **Low-volume sources**: Use shorter intervals (15min-1 hour)
- **Development/testing**: Use manual sync to control API usage

### Filtering

- Start with restrictive filters and expand as needed
- Use label/repository filters to reduce noise
- Set reasonable max_results limits
- Monitor storage usage

### Error Handling

- Check connector status regularly
- Review error messages for authentication issues
- Re-authenticate if tokens expire
- Contact support for persistent errors

### API Quotas

- Be aware of service provider rate limits
- Use appropriate sync intervals
- Monitor API usage in service dashboards
- Implement filters to reduce API calls

### Security

- Rotate encryption keys periodically
- Review connected apps in service provider settings
- Use environment variables for secrets
- Never commit credentials to version control

## Troubleshooting

### Common Issues

**Connector shows "Disconnected"**
- Credentials may have expired
- Re-authenticate via the UI

**Sync fails repeatedly**
- Check error message in connector details
- Verify API quotas not exceeded
- Ensure service is accessible

**No events appearing**
- Check sync job status for errors
- Verify filters aren't too restrictive
- Confirm data exists in external service

**"Encryption key not configured"**
- Generate and set CONNECTOR_ENCRYPTION_KEY
- Restart TVOS after configuration

### Getting Help

- Check connector-specific setup guides
- Review error messages in connector details
- Consult API documentation for external services
- Check TVOS logs for detailed error information

## Extending Connectors

### Adding New Connectors

TVOS uses a plugin-based connector architecture. To add a new connector:

1. Implement the `ConnectorBase` interface
2. Define OAuth flow or API authentication
3. Implement `fetch_events()` to retrieve data
4. Implement `transform_event()` to convert to EventPayload
5. Register connector in the ConnectorRegistry

See the [Developer Guide](./developer-guide.md) for details.

### Custom Connectors

The connector SDK allows you to create custom integrations:
- Implement standard interface
- Handle authentication your way
- Transform data to TVOS format
- Leverage existing infrastructure

## Roadmap

### Upcoming Connectors

- **GitHub**: Repository activity and code changes
- **Slack**: Messages and channel activity
- **Jira**: Issues, comments, and project updates
- **Calendar**: Google Calendar and Outlook events
- **Twitter/X**: Tweets and mentions

### Planned Features

- Bi-directional sync (write back to services)
- Webhook support for real-time updates
- Connector marketplace
- Custom connector SDK
- Multi-user support
- Team sharing

## Learn More

- [Gmail Connector Setup](./gmail-connector-setup.md)
- [API Reference](./api-reference.md)
- [Privacy & Security](./privacy-security.md)
- [Developer Guide](./developer-guide.md)
