# TVOS Documentation

Welcome to the TVOS (Temporal Vector OLAP System) documentation!

## Getting Started

- [Quick Start Guide](../README.md) - Get TVOS up and running
- [Architecture Overview](../ARCHITECTURE.md) - Understand how TVOS works

## Features

### Connectors
- [Connectors Overview](./connectors-overview.md) - Introduction to external integrations
- [Gmail Connector Setup](./gmail-connector-setup.md) - Connect your Gmail account

### Core Capabilities
- **Event Ingestion** - Collect events from multiple sources
- **Semantic Embeddings** - Automatic vector generation for semantic search
- **Temporal Analytics** - Analyze patterns and drift over time
- **Real-time Dashboard** - Visualize events and analytics

## User Guides

### Connectors
1. [Setting up Gmail](./gmail-connector-setup.md)
2. Managing connector sync schedules
3. Filtering and configuring data collection
4. Troubleshooting connector issues

### Analytics
1. Semantic search across events
2. Drift detection and analysis
3. Clustering similar events
4. Time-window queries

### TVQL
1. Query language basics
2. Advanced filtering
3. Aggregations and grouping

## API Reference

### REST Endpoints
- `/connectors` - Manage external integrations
- `/query` - Query events and analytics
- `/analytics` - Drift detection and clustering
- `/chat` - LLM-powered insights

### WebSocket
- Real-time event streaming
- Live analytics updates

## Configuration

### Environment Variables
```bash
# Database
DUCKDB_PATH=tvos.duckdb

# Services
REDIS_HOST=localhost
REDIS_PORT=6379
WEAVIATE_URL=http://localhost:8080

# Connectors
CONNECTOR_ENCRYPTION_KEY=<generated-key>
GMAIL_CLIENT_ID=<your-client-id>
GMAIL_CLIENT_SECRET=<your-client-secret>

# LLM (optional)
LLM_PROVIDER=gemini|openai|anthropic
GEMINI_API_KEY=<your-key>
```

### Docker Compose
- Service configuration
- Port mappings
- Volume mounts
- Environment overrides

## Security & Privacy

### Data Storage
- Local-first architecture
- No external data transmission
- Encrypted credential storage
- User-controlled data retention

### Authentication
- OAuth 2.0 for external services
- Read-only access scopes
- Token encryption at rest
- Easy credential revocation

### Best Practices
- Secure environment variables
- Regular credential rotation
- Audit connected services
- Monitor API usage

## Troubleshooting

### Common Issues

**Database locked errors**
- Use the shared connection from `tvos.db.get_db_connection()`
- Never create multiple DuckDB connections

**Connector authentication failures**
- Verify OAuth credentials in `.env`
- Check redirect URI configuration
- Ensure API is enabled in service console

**Missing embeddings**
- Check Weaviate is running: `docker compose ps`
- Verify embedding worker is active
- Check Redis queue: `redis-cli llen tvos:queue:embedding`

**UI not loading**
- Verify API is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Ensure correct API URL in UI config

### Getting Help

1. Check relevant documentation section
2. Review error messages and logs
3. Search GitHub issues
4. Open a new issue with details

## Development

### Technology Stack
- **Backend**: Python, FastAPI, DuckDB, Weaviate, Redis
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **ML**: sentence-transformers, scikit-learn, HDBSCAN
- **Infrastructure**: Docker Compose, Prometheus

### Contributing
- Code style guidelines
- Testing requirements
- Pull request process
- Connector development guide

### Testing
```bash
# Run tests
pytest

# Check database
python scripts/check_db.py

# Verify embeddings
python scripts/check_embeddings.py

# Test connectors
python scripts/verify_connectors.py
```

## Roadmap

### Near-term
- GitHub connector
- Webhook support
- Enhanced filtering
- Performance optimizations

### Long-term
- Additional connectors (Slack, Jira, Calendar)
- Bi-directional sync
- Multi-user support
- Connector marketplace
- Custom connector SDK

## Resources

### Documentation
- [Project README](../README.md)
- [Architecture](../ARCHITECTURE.md)
- [RFC](../RFC.md)

### External Links
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Gmail API Reference](https://developers.google.com/gmail/api)

## Support

### Community
- GitHub Issues
- Discussions
- Contributing guidelines

### Documentation Updates
This documentation is continuously updated. Last updated: 2024

---

**Quick Links:**
- [Connectors Overview](./connectors-overview.md)
- [Gmail Setup](./gmail-connector-setup.md)
- [Main README](../README.md)
