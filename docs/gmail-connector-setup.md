# Gmail Connector Setup Guide

## Overview

The Gmail connector allows TVOS to ingest your email data for temporal semantic analysis. This guide walks you through setting up Gmail integration with TVOS.

## Prerequisites

- A Google account with Gmail
- TVOS installed and running
- Access to Google Cloud Console

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID for reference

## Step 2: Enable Gmail API

1. In the Google Cloud Console, navigate to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click on "Gmail API" and click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless you have a Google Workspace)
3. Fill in the required fields:
   - **App name**: TVOS Gmail Connector
   - **User support email**: Your email
   - **Developer contact email**: Your email
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes**
6. Add the following scope:
   - `https://www.googleapis.com/auth/gmail.readonly`
7. Click **Save and Continue**
8. Add your email as a test user (required for external apps in testing mode)
9. Click **Save and Continue**

## Step 4: Create OAuth Credentials

1. Navigate to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Choose **Web application** as the application type
4. Configure the OAuth client:
   - **Name**: TVOS Gmail Connector
   - **Authorized redirect URIs**: Add `http://localhost:8000/connectors/gmail/callback`
5. Click **Create**
6. Copy the **Client ID** and **Client Secret** - you'll need these next

## Step 5: Configure TVOS

1. Open your `.env` file in the TVOS root directory
2. Add your Gmail OAuth credentials:

```bash
# Gmail Connector Configuration
GMAIL_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret_here
```

3. If you haven't already, generate an encryption key for storing credentials:

```bash
# Generate encryption key (run this once)
python -c "from tvos.connectors import CredentialEncryption; print(CredentialEncryption.generate_key())"
```

4. Add the encryption key to your `.env`:

```bash
CONNECTOR_ENCRYPTION_KEY=your_generated_key_here
```

5. Restart TVOS to load the new configuration:

```bash
docker compose restart api
```

## Step 6: Connect Gmail in TVOS UI

1. Open the TVOS dashboard at `http://localhost:3000`
2. Navigate to the **Connectors** section
3. Find **Gmail** in the list of available connectors
4. Click **Connect**
5. You'll be redirected to Google's OAuth consent screen
6. Review the permissions (read-only access to Gmail)
7. Click **Allow**
8. You'll be redirected back to TVOS with a success message

## Step 7: Configure Sync Settings

After connecting, you can configure how TVOS syncs your Gmail data:

1. Click on the **Gmail** connector to view details
2. Configure sync settings:
   - **Sync Interval**: Choose how often to sync (15min, 1hr, 6hr, 24hr, or manual)
   - **Labels**: Optionally filter by specific Gmail labels (e.g., "INBOX", "IMPORTANT")
   - **Max Results**: Limit the number of emails fetched per sync

3. Click **Save Configuration**

## Step 8: Trigger Initial Sync

1. Click **Sync Now** to perform the first sync
2. Monitor the sync progress in the UI
3. Once complete, your Gmail events will appear in the event stream

## Data Privacy

### What Data is Collected

The Gmail connector collects:
- Email subject lines
- Sender and recipient addresses
- Email body content (text only)
- Timestamps
- Gmail labels
- Thread IDs

### What Data is NOT Collected

- Attachments
- Email headers (except From, To, Subject, Date)
- Deleted emails
- Spam folder contents

### Data Storage

- All credentials are encrypted using AES-256-GCM encryption
- Credentials are stored locally in your TVOS database
- Email content is stored locally and never sent to external services
- TVOS is local-first - your data stays on your machine

## Filtering Options

### Filter by Labels

To sync only specific Gmail labels:

```json
{
  "labels": ["INBOX", "IMPORTANT"]
}
```

### Limit Results

To limit the number of emails per sync:

```json
{
  "max_results": 100
}
```

### Combined Filters

```json
{
  "labels": ["INBOX"],
  "max_results": 50
}
```

## Troubleshooting

### "OAuth credentials not configured" Error

**Solution**: Verify that `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` are set in your `.env` file and restart TVOS.

### "Encryption key not configured" Error

**Solution**: Generate and set `CONNECTOR_ENCRYPTION_KEY` in your `.env` file.

### "Failed to exchange authorization code" Error

**Solution**: 
- Verify your redirect URI in Google Cloud Console matches exactly: `http://localhost:8000/connectors/gmail/callback`
- Check that the Gmail API is enabled in your Google Cloud project
- Ensure your OAuth consent screen is configured correctly

### "Access token expired" Error

**Solution**: The connector will automatically refresh tokens. If this persists, disconnect and reconnect the Gmail connector.

### Sync Fails with "Rate limit exceeded"

**Solution**: TVOS will automatically back off and retry. Consider increasing your sync interval to avoid hitting Gmail API quotas.

### No Emails Appearing After Sync

**Solution**:
- Check the sync job status for errors
- Verify your label filters aren't too restrictive
- Ensure you have emails in your Gmail account that match the sync criteria

## Rate Limits

Gmail API has the following rate limits:
- 250 requests per second per user
- 1 billion requests per day (shared across all users)

TVOS automatically handles rate limiting with exponential backoff.

## Disconnecting Gmail

To disconnect Gmail from TVOS:

1. Navigate to **Connectors** > **Gmail**
2. Click **Disconnect**
3. Confirm the action

This will:
- Remove stored credentials
- Stop automatic syncing
- Preserve existing synced email data

To also delete synced data, use the TVOS data management tools.

## Security Best Practices

1. **Keep credentials secure**: Never commit your `.env` file to version control
2. **Use test users**: Keep your OAuth app in testing mode unless you need public access
3. **Regular audits**: Periodically review connected apps in your [Google Account settings](https://myaccount.google.com/permissions)
4. **Revoke access**: If you suspect credential compromise, revoke access in Google Account settings and reconnect

## Next Steps

- Explore semantic search across your emails
- Analyze email patterns with drift detection
- Cluster similar emails by topic
- Query emails using TVQL

For more information, see:
- [TVOS User Guide](./user-guide.md)
- [Connector API Reference](./api-reference.md)
- [Privacy & Security](./privacy-security.md)
