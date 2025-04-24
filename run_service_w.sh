#!/usr/bin/env bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage information
function show_usage {
    cat <<EOF
Usage: $0 [service_name] [options]

Available services:
  users         - Run the users service
  rabbitmq      - Run the RabbitMQ service
  auth          - Run the authentication service
  notifications - Run the notifications service
  presence      - Run the presence service
  socket_io     - Run the socket_io service
  chat          - Run the chat service
  -a, --all     - Run all services in separate processes
  stop SERVICE  - Stop a specific running service
  stop-all      - Stop all running services
  status        - Check the status of all services

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
    local port_arg=$2    # Use a different name to avoid conflict with the 'PORT' global variable
    local workers_arg=$3 # Use a different name to avoid conflict with the 'WORKERS' global variable
    local os_type=$4

    cd "$SERVICE_DIR"
    export PYTHONPATH="${PROJECT_ROOT}"
    echo "PYTHONPATH set to: $PYTHONPATH" >>"${SERVICE_DIR}/logs/${service}.log"

    case $service in
    users)
        DEFAULT_PORT=8005
        SERVICE_DIR="${PROJECT_ROOT}/services/users"
        ;;
    rabbitmq)
        # DEFAULT_PORT=8006
        # SERVICE_DIR="${PROJECT_ROOT}/services/rabbitmq"
        DEFAULT_PORT=5672                               # Default AMQP port
        SERVICE_DIR="${PROJECT_ROOT}/services/rabbitmq" # Assuming structure
        echo "Skipping automatic run for RabbitMQ service."
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
    socket_io)
        DEFAULT_PORT=8010
        SERVICE_DIR="${PROJECT_ROOT}/services/socket_io"
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

    # Load environment variables from the root .env file
    ENV_SH_FILE="${PROJECT_ROOT}/services/.env.sh"
    if [[ -f "$ENV_SH_FILE" ]]; then

        echo "Loading environment variables from: $ENV_SH_FILE"
        source "$ENV_SH_FILE"
        # Export other required variables that match what Pydantic expects
        export DATABASE_URL="$PG_CONNECTION_STRING"
        export POSTGRES_USER="$PG_USER"
        export POSTGRES_PASSWORD="$PG_PASSWORD"
        export POSTGRES_HOST="$PG_HOST"
        export POSTGRES_PORT="$PG_PORT"
        export POSTGRES_DB="$PG_DATABASE"

        echo "Environment variables loaded."
    else
        echo "Warning: No .env.sh file found at $ENV_SH_FILE"
        echo "Make sure all required environment variables are set."
        echo "Using default values for the following environment variables:"
        echo "DATABASE_URL, RABBITMQ_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, JWT_SECRET_KEY"
        echo "You can create a .env file in the project root directory to override these defaults."
        echo "Example .env file content:"
        echo "DATABASE_URL=postgresql://your_user:your_password@localhost:5432/your_db"
        echo "RABBITMQ_URL=amqp://guest:guest@localhost:5672/"
        echo "POSTGRES_USER=your_user"
        echo "POSTGRES_PASSWORD=your_password"
        echo "POSTGRES_HOST=localhost"
        echo "POSTGRES_PORT=5432"
        echo "POSTGRES_DB=your_db"
        echo "JWT_SECRET_KEY=your_secret_key"
        echo "You can also set these variables directly in your shell before running the script."
        # Get the enivronment variables from the .env file
        export DATABASE_URL="postgresql://sahdude:CS467@209.46.124.94:5432/postgres"
        export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
        export POSTGRES_USER="sahdude"
        export POSTGRES_PASSWORD="CS467"
        export POSTGRES_HOST="209.46.124.94"
        export POSTGRES_PORT="5432"
        export POSTGRES_DB="postgres"
        export JWT_SECRET_KEY="your_secret_key"
    fi

    # Check if the service directory exists
    if [[ ! -d "$SERVICE_DIR" ]]; then
        echo "Error: Service directory not found: $SERVICE_DIR"
        # Don't exit if running all, just skip this one
        if [[ "$RUN_ALL" != true ]]; then
            exit 1
        else
            echo "Skipping service $service..."
            return
        fi
    fi

    # Check if app/main.py exists (basic check)
    if [[ ! -f "$SERVICE_DIR/app/main.py" ]]; then
        echo "Warning: No app/main.py found in $SERVICE_DIR for service $service. Skipping run."
        return
    fi

    # Change to the service directory
    echo "--- Running Service: $service ---"
    pushd "$SERVICE_DIR" >/dev/null # Use pushd/popd to manage directory changes safely
    echo "Changed directory to: $(pwd)"

    # --- Install/Update dependencies from service-specific requirements ---
    local SERVICE_REQS="requirements.txt"
    if [[ -f "$SERVICE_REQS" ]]; then
        echo "Checking/installing dependencies from $SERVICE_DIR/$SERVICE_REQS..."
        pip install -r "$SERVICE_REQS"
    else
        echo "No service-specific requirements.txt found in $SERVICE_DIR."
    fi
    # --------------------------------------------------------------------

    local actual_port=${port_arg:-$DEFAULT_PORT}
    # Run the service based on OS
    if [[ "$os_type" == "windows" ]]; then
        # Use uvicorn directly on Windows
        echo "Starting $service service directly with uvicorn on port $actual_port (workers option ignored)..."
        # Use start /B for background execution on Windows if running all

        if [[ "$RUN_ALL" == true ]]; then

            mkdir -p "${SERVICE_DIR}/logs"
            # Run with nohup AND disown to fully detach from the terminal session
            nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $actual_port --log-level info >"${SERVICE_DIR}/logs/${service}.log" 2>&1 &
            local pid=$!
            disown $pid # This fully detaches the process from the terminal
            echo $pid >"${SERVICE_DIR}/logs/${service}.pid"
            echo "Started ${service} with PID $pid"

        else
            python -m uvicorn app.main:app --host 0.0.0.0 --port $actual_port --log-level info
        fi
    else
        # Use Gunicorn with Uvicorn worker on Linux/macOS
        echo "Starting $service service with gunicorn on port $actual_port with $actual_workers worker(s)..."
        # Run in background using '&' for Linux/macOS if running all
        if [[ "$RUN_ALL" == true ]]; then
            gunicorn app.main:app \
                --workers $actual_workers \
                --worker-class uvicorn.workers.UvicornWorker \
                --bind 0.0.0.0:$actual_port \
                --log-level info \
                --access-logfile - \
                --error-logfile - \
                --timeout 120 &
        else
            gunicorn app.main:app \
                --workers $actual_workers \
                --worker-class uvicorn.workers.UvicornWorker \
                --bind 0.0.0.0:$actual_port \
                --log-level info \
                --access-logfile - \
                --error-logfile - \
                --timeout 120
        fi
    fi

    sleep 2
    if kill -0 $(cat "${SERVICE_DIR}/logs/${service}.pid") 2>/dev/null; then
        echo "${service} service is running successfully."
    else
        echo "WARNING: ${service} service may have terminated. Check ${SERVICE_DIR}/logs/${service}.log for errors."
    fi

    popd >/dev/null # Return to the original directory
    echo "--- Finished setup for Service: $service ---"
    echo "" # Add a newline for better readability
}

function stop_service {
    local service=$1

    case $service in
    users | auth | notifications | presence | socket_io | chat)
        SERVICE_DIR="${PROJECT_ROOT}/services/$service"
        ;;
    rabbitmq)
        SERVICE_DIR="${PROJECT_ROOT}/services/rabbitmq"
        ;;
    *)
        echo "Error: Unknown service: $service"
        show_usage
        exit 1
        ;;
    esac

    # Check if PID file exists
    PID_FILE="${SERVICE_DIR}/logs/${service}.pid"
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        echo "Stopping $service (PID: $PID)..."

        # Check if process is running
        if kill -0 $PID 2>/dev/null; then
            # Kill process
            kill $PID
            echo "Service $service stopped."
        else
            echo "Process $PID for service $service is not running."
        fi

        # Remove PID file
        rm "$PID_FILE"
    else
        echo "No PID file found for $service. Service may not be running or was started manually."
    fi
}

function check_service_logs {
    local service=$1
    SERVICE_DIR="${PROJECT_ROOT}/services/$service"
    LOG_FILE="${SERVICE_DIR}/logs/${service}.log"

    if [[ -f "$LOG_FILE" ]]; then
        echo "Last 20 lines of $service log:"
        tail -n 20 "$LOG_FILE"
    else
        echo "No log file found for $service"
    fi
}

# Detect OS
OS_TYPE="linux" # Default
VENV_ACTIVATE_PATH="${PROJECT_ROOT}/venv/bin/activate"

if [[ "$(uname -s)" == *"MINGW64_NT"* || "$(uname -s)" == *"MSYS_NT"* || "$(uname -s)" == "CYGWIN_NT"* ]]; then
    OS_TYPE="windows"
    VENV_ACTIVATE_PATH="${PROJECT_ROOT}/venv/Scripts/activate"
    echo "Detected Windows environment (MINGW/MSYS/Cygwin)."
elif [[ "$(uname -s)" == "Darwin" ]]; then
    OS_TYPE="macos"
    echo "Detected macOS environment."
else
    echo "Detected Linux environment."
fi

# Parse command line arguments
SERVICE=""
PORT=""
WORKERS=1
RUN_ALL=false

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
    stop)
        if [[ -n "$2" ]]; then
            stop_service "$2"
            exit 0
        else
            echo "Error: stop requires a service name" >&2
            show_usage
            exit 1
        fi
        ;;
    stop-all)
        for service in "users" "auth" "notifications" "presence" "socket_io" "chat"; do
            stop_service "$service"
        done
        exit 0
        ;;
    status)
        echo "Checking service status..."
        for service in "users" "auth" "notifications" "presence" "socket_io" "chat"; do
            SERVICE_DIR="${PROJECT_ROOT}/services/$service"
            PID_FILE="${SERVICE_DIR}/logs/${service}.pid"
            if [[ -f "$PID_FILE" ]]; then
                PID=$(cat "$PID_FILE")
                if kill -0 $PID 2>/dev/null; then
                    echo "$service: RUNNING (PID: $PID)"
                else
                    echo "$service: STOPPED (stale PID file: $PID)"
                fi
            else
                echo "$service: NOT RUNNING"
            fi
        done
        exit 0
        ;;
    --port=*)
        PORT="${key#*=}"
        shift # past argument=value
        ;;
    --port)
        if [[ -n "$2" ]] && [[ "$2" != -* ]]; then
            PORT="$2"
            shift # past argument
            shift # past value
        else
            echo "Error: --port requires a value" >&2
            exit 1
        fi
        ;;
    --workers=*)
        WORKERS="${key#*=}"
        shift # past argument=value
        ;;
    --workers)
        if [[ -n "$2" ]] && [[ "$2" != -* ]]; then
            WORKERS="$2"
            shift # past argument
            shift # past value
        else
            echo "Error: --workers requires a value" >&2
            exit 1
        fi
        ;;
    -a | --all)
        RUN_ALL=true
        shift # past argument
        ;;
    --help)
        show_usage
        exit 0
        ;;
    -*)
        # Handle unknown options
        echo "Error: Unknown option: $1" >&2
        show_usage
        exit 1
        ;;
    *)
        # Assume it's the service name if not already set
        if [[ -z "$SERVICE" ]]; then
            SERVICE="$1"
            shift # past argument
        else
            # If service is already set, this is an unknown positional argument
            echo "Error: Unexpected argument: $1" >&2
            show_usage
            exit 1
        fi
        ;;
    esac
done

# Activate the virtual environment if the activation script is found
if [[ -f "$VENV_ACTIVATE_PATH" ]]; then
    echo "Activating virtual environment using: $VENV_ACTIVATE_PATH"
    source "$VENV_ACTIVATE_PATH"
else
    echo "Warning: Virtual environment activation script not found at $VENV_ACTIVATE_PATH"
    echo "Please ensure a virtual environment exists at ${PROJECT_ROOT}/venv"
    # echo "Attempting to continue without activating virtual environment..."
    # Optionally exit if venv is critical:
    echo "Error: Cannot proceed without virtual environment." >&2
    exit 1
fi

# Add the project root to PYTHONPATH (useful for imports across services)
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
echo "Added ${PROJECT_ROOT} to PYTHONPATH"
echo "" # Add a newline

# --- Execution Logic ---

if [[ "$RUN_ALL" == true ]]; then
    echo "Starting all services..."
    SERVICES=("users" "auth" "notifications" "presence" "socket_io" "chat") # Define the list of services
    PIDS=()                                                                 # Array to store background process IDs (for non-Windows)

    for service in "${SERVICES[@]}"; do
        # Pass OS_TYPE to the function
        run_service "$service" "$PORT" "$WORKERS" "$OS_TYPE"
        if [[ "$OS_TYPE" != "windows" && $? -eq 0 && "$service" != "rabbitmq" ]]; then
            PIDS+=($!) # Store the PID of the last background process on Linux/macOS
        fi
    done

    echo "-----------------------------------------------------"
    echo "All requested services have been launched."
    if [[ "$OS_TYPE" == "windows" ]]; then
        echo "Services are running in separate background windows."
        echo "Check Task Manager or use 'tasklist' to see python processes."
        echo "Press Ctrl+C in this window to exit the script (may not stop background services)."
        echo "Use './run_service_w.sh stop <service>' to stop a specific service."
        echo "Use './run_service_w.sh stop-all' to stop all services."
        # Keep script alive briefly to show messages
        sleep 5
    else
        echo "Services are running in the background (PIDs: ${PIDS[*]})."
        echo "Use 'kill <PID>' or 'pkill -f gunicorn' to stop them."
        echo "Press Ctrl+C to stop this script (will not stop background services)."
        echo "Use './run_service_w.sh stop <service>' to stop a specific service."
        echo "Use './run_service_w.sh stop-all' to stop all services."
        # Wait indefinitely until script is interrupted
        wait
    fi

else
    # Run a single specified service
    if [[ -z "$SERVICE" ]]; then
        echo "Error: No service specified and --all not used." >&2
        show_usage
        exit 1
    fi
    # Pass OS_TYPE to the function
    run_service "$SERVICE" "$PORT" "$WORKERS" "$OS_TYPE"

    # If running a single service directly (not backgrounded on Windows)
    # the script will stay attached to it. Ctrl+C will stop it.
    if [[ "$OS_TYPE" == "windows" ]]; then
        echo "Service $SERVICE is running. Press Ctrl+C to stop."
    fi
    # For Linux/macOS single service, gunicorn runs in foreground by default here
fi

echo "Script finished."
