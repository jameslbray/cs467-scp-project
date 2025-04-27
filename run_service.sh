#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set Python path to include project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Function to display usage
usage() {
    echo "Usage: $0 [service]"
    echo "Available services:"
    echo "  users         - Run the users service"
    echo "  rabbitmq      - Run the RabbitMQ service"
    echo "  notifications - Run the notifications service"
    echo "  presence      - Run the presence service"
    echo "  socket-io     - Run the Socket.IO service"
    echo "  chat          - Run the chat service"
    echo "  all           - Run all services"
    exit 1
}

# Function to run a specific service
run_service() {
    local service=$1
    local SERVICE_DIR

    case $service in
        users)
            SERVICE_DIR="${PROJECT_ROOT}/services/users"
            ;;
        rabbitmq)
            SERVICE_DIR="${PROJECT_ROOT}/services/rabbitmq"
            ;;
        notifications)
            SERVICE_DIR="${PROJECT_ROOT}/services/notifications"
            ;;
        presence)
            SERVICE_DIR="${PROJECT_ROOT}/services/presence"
            ;;
        socket-io)
            SERVICE_DIR="${PROJECT_ROOT}/services/socket_io"
            ;;
        chat)
            SERVICE_DIR="${PROJECT_ROOT}/services/chat"
            ;;
        *)
            echo "Unknown service: $service"
            usage
            ;;
    esac

    if [ ! -d "$SERVICE_DIR" ]; then
        echo "Service directory not found: $SERVICE_DIR"
        exit 1
    fi

    echo "Starting $service service..."
    cd "$SERVICE_DIR" || exit 1

    # Check if requirements.txt exists and install dependencies
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
    fi

    # Run the service
    if [ -f "run.sh" ]; then
        ./run.sh
    else
        # Default run command for Python services
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    fi
}

# Function to run all services
run_all() {
    local services=("users" "rabbitmq" "notifications" "presence" "socket-io" "chat")

    for service in "${services[@]}"; do
        run_service "$service" &
    done

    # Wait for all background processes
    wait
}

# Main script
if [ $# -eq 0 ]; then
    usage
fi

case $1 in
    all)
        run_all
        ;;
    *)
        run_service "$1"
        ;;
esac