#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Activate the virtual environment
source "${PROJECT_ROOT}/venv/bin/activate"

# Set environment variables if needed
# export ENV_VAR=value

# Set the working directory
cd "$(dirname "${BASH_SOURCE[0]}")"

# Run Gunicorn with Uvicorn worker
# Using 1 worker as this service might need WebSocket support
exec gunicorn app.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8004 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --timeout 120

