#!/bin/bash

# Start all collectors in background
python3 scripts/ingest_shell_history.py &
python3 scripts/ingest_browser_history.py &
python3 scripts/ingest_system_metrics.py &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?

