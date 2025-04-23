#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage information
function show_usage {
    echo "Usage: $0 [service_name] [options]"
    echo ""
    echo "Available services:"
    echo "  users         - Run the users service"
    echo "  rabbitmq      - Run the RabbitMQ service"
    echo "  auth          - Run the authentication service"
    echo "  notifications - Run the notifications service"
    echo "  presence      - Run the presence service"
    echo "  socket-io     - Run the socket-io service"
    echo "  chat          - Run the chat service"
    echo ""
    echo "Options:"
    echo "  --port PORT   - Specify a custom port (default varies by service)"
    echo "  --workers N   - Specify number of workers (default: 1)"
    echo "  --help        - Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 users --port 8005 --workers 2"
}

# Parse command line arguments
SERVICE=""
PORT=""
WORKERS=1
for arg in "$@"; do
    case $arg in
        --port=*)
        PORT="${arg#*=}"
        shift
        ;;
        --port)
        PORT="$2"
        shift
        shift
        ;;
        --workers=*)
        WORKERS="${arg#*=}"
        shift
        ;;
        --workers)
        WORKERS="$2"
        shift
        shift
        ;;
        --help)
        show_usage
        exit 0
        ;;
        *)
        if [[ -z "$SERVICE" ]]; then
            SERVICE="$arg"
        fi
        ;;
    esac
done

# Check if a service was specified
if [[ -z "$SERVICE" ]]; then
    echo "Error: No service specified"
    show_usage
    exit 1
fi

# Activate the virtual environment if it exists
if [[ -d "${PROJECT_ROOT}/venv" ]]; then
    echo "Activating virtual environment..."
    source "${PROJECT_ROOT}/venv/bin/activate"
else
    echo "Warning: Virtual environment not found at ${PROJECT_ROOT}/venv"
    echo "Continuing without activating virtual environment..."
fi

# Add the project root to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
echo "Added ${PROJECT_ROOT} to PYTHONPATH"

# Set default ports for each service
case $SERVICE in
    users)
        DEFAULT_PORT=8005
        SERVICE_DIR="${PROJECT_ROOT}/services/users"
        ;;
    rabbitmq)
        DEFAULT_PORT=8006
        SERVICE_DIR="${PROJECT_ROOT}/services/rabbitmq"
        ;;
    auth)
        DEFAULT_PORT=8007
        SERVICE_DIR="${PROJECT_ROOT}/services/auth"
        ;;
    notifications)
        DEFAULT_PORT=8008
        SERVICE_DIR="${PROJECT_ROOT}/services/notifications"
        ;;
    presence)
        DEFAULT_PORT=8009
        SERVICE_DIR="${PROJECT_ROOT}/services/presence"
        ;;
    socket-io)
        DEFAULT_PORT=8010
        SERVICE_DIR="${PROJECT_ROOT}/services/socket-io"
        ;;
    chat)
        DEFAULT_PORT=8011
        SERVICE_DIR="${PROJECT_ROOT}/services/chat"
        ;;
    *)
        echo "Error: Unknown service: $SERVICE"
        show_usage
        exit 1
        ;;
esac

# Use custom port if specified, otherwise use default
PORT=${PORT:-$DEFAULT_PORT}

# Check if the service directory exists
if [[ ! -d "$SERVICE_DIR" ]]; then
    echo "Error: Service directory not found: $SERVICE_DIR"
    exit 1
fi

# Change to the service directory
cd "$SERVICE_DIR"
echo "Changed directory to: $SERVICE_DIR"

# Run the service with Gunicorn and Uvicorn worker
echo "Starting $SERVICE service on port $PORT with $WORKERS worker(s)..."
exec gunicorn app.main:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --reload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 