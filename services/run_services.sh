#!/bin/bash

# Function to run a service
run_service() {
    local service=$1
    local port=$2
    echo "Starting $service service on port $port..."
    cd "$service" && \
    PORT=$port gunicorn -c gunicorn_config.py &
    cd ..
}

# Kill any existing Gunicorn processes
pkill -f gunicorn

# Run each service on a different port
run_service "presence" "8000"
run_service "chat" "8001"
run_service "socket-io" "8002"
run_service "auth" "8003"
run_service "notifications" "8004"
run_service "users" "8005"

# Wait for all background processes
wait 