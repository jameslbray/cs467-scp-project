#!/usr/bin/env bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage information
function show_usage {
    cat << EOF
Usage: $0 [service_name] [options]

Available services:
  users         - Run the users service
  rabbitmq      - Run the RabbitMQ service
  auth          - Run the authentication service
  notifications - Run the notifications service
  presence      - Run the presence service
  socket-io     - Run the socket-io service
  chat          - Run the chat service
  -a, --all     - Run all services in separate processes

Options:
  --port PORT   - Specify a custom port (default varies by service)
  --workers N   - Specify number of workers (default: 1)
  --help        - Show this help message

Examples:
  $0 users --port 8005 --workers 2
  $0 -a     # Run all services
EOF
}

# Function to run a single service
function run_service {
    local service=$1
    local port=$2
    local workers=$3

    case $service in
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
            echo "Error: Unknown service: $service"
            show_usage
            exit 1
            ;;
    esac

    # Use custom port if specified, otherwise use default
    local actual_port=${port:-$DEFAULT_PORT}
    local actual_workers=${workers:-1}

    # Check if the service directory exists
    if [[ ! -d "$SERVICE_DIR" ]]; then
        echo "Error: Service directory not found: $SERVICE_DIR"
        exit 1
    fi

    # Change to the service directory
    cd "$SERVICE_DIR"
    echo "Changed directory to: $SERVICE_DIR"

    # Run the service with Gunicorn and Uvicorn worker
    echo "Starting $service service on port $actual_port with $actual_workers worker(s)..."
    # Set environment variables to force standard asyncio
    export UVICORN_LOOP=asyncio
    export UVICORN_HTTP=auto
    export UVICORN_USE_UVLOOP=0

    gunicorn app.main:app \
        --workers $actual_workers \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:$actual_port \
        --reload \
        --log-level info \
        --access-logfile - \
        --error-logfile - \
        --timeout 120 &
}

# Parse command line arguments
SERVICE=""
PORT=""
WORKERS=1
RUN_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --port)
            if [[ -n "$2" ]] && [[ "$2" != -* ]]; then
                PORT="$2"
                shift 2
            else
                echo "Error: --port requires a value"
                exit 1
            fi
            ;;
        --workers=*)
            WORKERS="${1#*=}"
            shift
            ;;
        --workers)
            if [[ -n "$2" ]] && [[ "$2" != -* ]]; then
                WORKERS="$2"
                shift 2
            else
                echo "Error: --workers requires a value"
                exit 1
            fi
            ;;
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$SERVICE" ]]; then
                SERVICE="$1"
            fi
            shift
            ;;
    esac
done

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

# Run all services if requested
if [[ "$RUN_ALL" == true ]]; then
    echo "Starting all services..."
    SERVICES=("users" "rabbitmq" "auth" "notifications" "presence" "socket-io" "chat")
    for service in "${SERVICES[@]}"; do
        run_service "$service" "$PORT" "$WORKERS"
    done
    echo "All services started. Press Ctrl+C to stop all services."
    wait
else
    # Check if a service was specified
    if [[ -z "$SERVICE" ]]; then
        echo "Error: No service specified"
        show_usage
        exit 1
    fi
    run_service "$SERVICE" "$PORT" "$WORKERS"
fi