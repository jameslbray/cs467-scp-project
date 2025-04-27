#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE_PATH="${PROJECT_ROOT}/venv/Scripts/activate"

# Activate the virtual environment
if [[ -f "$VENV_ACTIVATE_PATH" ]]; then
    echo "Activating virtual environment..."
    source "$VENV_ACTIVATE_PATH"
else
    echo "Error: Virtual environment not found at $VENV_ACTIVATE_PATH"
    exit 1
fi

# Install/upgrade core dependencies
echo "Installing/upgrading core dependencies..."
pip install --upgrade pip
pip install --upgrade redis
pip install --upgrade pymongo==4.5.0
pip install --upgrade motor==3.3.2
pip install --upgrade python-socketio[asyncio_client]

# Check each service's requirements
echo "Installing service-specific dependencies..."
for service in "users" "auth" "notifications" "presence" "socket-io" "chat"; do
    SERVICE_DIR="${PROJECT_ROOT}/services/$service"

    if [[ -d "$SERVICE_DIR" ]]; then
        if [[ -f "${SERVICE_DIR}/requirements.txt" ]]; then
            echo "Installing dependencies for $service..."
            pip install -r "${SERVICE_DIR}/requirements.txt"
        else
            echo "No requirements.txt found for $service, skipping..."
        fi
    else
        echo "Service directory not found: $SERVICE_DIR, skipping..."
    fi
done

echo "Dependencies setup complete."
