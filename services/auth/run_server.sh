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
exec gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8002 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --timeout 120

