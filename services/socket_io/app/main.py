import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.presence.app.core.presence_manager import PresenceManager
from services.rabbitmq.core.client import RabbitMQClient
from services.rabbitmq.core.config import Settings as RabbitMQSettings
from services.shared.utils.retry import CircuitBreaker, with_retry
from services.socket_io.app.core.config import get_settings
from services.socket_io.app.core.events import AuthEvents
from services.socket_io.app.core.socket_server import SocketServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()
rabbitmq_settings = RabbitMQSettings(RABBITMQ_URL=os.getenv("RABBITMQ_URL"))

# Create circuit breaker for resilient operations
service_circuit_breaker = CircuitBreaker(
    "socket_io_service",
    failure_threshold=3,
    reset_timeout=30.0
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events handler with resilient initialization."""
    # Create RabbitMQ client first since other components depend on it
    rabbitmq_client = RabbitMQClient(rabbitmq_settings)

    # Create PresenceManager with RabbitMQ config
    presence_manager = PresenceManager(
        {
            "rabbitmq": {
                "url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
            }
        }
    )

    # Create SocketServer with dependencies injected
    socket_server = SocketServer(
        rabbitmq_client=rabbitmq_client,
        presence_manager=presence_manager,
        cors_allowed_origins="http://localhost:5173",  # Single string, not array
        debug_mode=True,
        cors_credentials=True,
        ping_timeout=20,
        ping_interval=25,
        max_http_buffer_size=5 * 1024 * 1024
    )

    # STARTUP
    logger.info("Starting Socket.IO service...")

    # Connect to RabbitMQ first
    try:
        await with_retry(
            rabbitmq_client.connect,
            max_attempts=5,
            initial_delay=2.0,
            max_delay=30.0,
            circuit_breaker=service_circuit_breaker
        )
        await rabbitmq_client.declare_exchange("auth", exchange_type="topic")
        await rabbitmq_client.declare_exchange("messages", exchange_type="topic")
        await rabbitmq_client.declare_exchange("presence", exchange_type="fanout")
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        # Continue anyway - we'll retry during operation

    # Initialize presence manager
    try:
        await with_retry(
            presence_manager.initialize,
            max_attempts=3,
            initial_delay=2.0,
            max_delay=15.0,
            circuit_breaker=service_circuit_breaker
        )
        logger.info("Presence manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize presence manager: {e}")
        # Continue anyway - the manager has internal retry logic

    # Initialize socket server
    try:
        await socket_server.initialize()
        logger.info("Socket server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize socket server: {e}")
        # Continue anyway - the server has internal retry logic

    # Initialize auth events - this registers Socket.IO event handlers through its constructor
    # Variable is named with underscore prefix to indicate it's used only for its side effects
    _auth_events = AuthEvents(socket_server.sio, rabbitmq_client)

    # Mount the Socket.IO ASGI app with its own CORS handling
    socketio_app = socket_server.get_asgi_app()
    app.mount("/socket.io", socketio_app, name="socket.io")

    logger.info("Socket.IO service started")

    yield

    # SHUTDOWN
    logger.info("Shutting down Socket.IO service...")

    # Shutdown in reverse order of initialization
    await socket_server.shutdown()
    await presence_manager.shutdown()
    await rabbitmq_client.close()

    logger.info("Socket.IO service shut down successfully")

# Create FastAPI app
app = FastAPI(title="Socket.IO Service", lifespan=lifespan)

# Configure CORS only for non-Socket.IO routes
# Custom CORS middleware that ignores Socket.IO routes
async def custom_cors_middleware(request: Request, call_next):
    if request.url.path.startswith("/socket.io/"):
        # Skip CORS handling for Socket.IO routes
        return await call_next(request)
        
    # Handle CORS for non-Socket.IO routes
    origin = request.headers.get("origin")
    if origin == "http://localhost:5173":
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
        
        if request.method == "OPTIONS":
            # Handle preflight requests
            return JSONResponse(content={}, headers=headers)
            
        # Handle actual requests
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        return response
        
    return await call_next(request)

# Add custom CORS middleware
app.middleware("http")(custom_cors_middleware)

# Add logging middleware to inspect request headers
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request path: {request.url.path}")
    if request.url.path.startswith("/socket.io"):
        logger.debug(f"Socket.IO request headers: {request.headers}")
    response = await call_next(request)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "socket_io"
    }

@app.options("/{rest_of_path:path}")
async def options_route(rest_of_path: str):
    """Handle OPTIONS requests for CORS preflight."""
    return {"status": "ok"}

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.SOCKET_IO_HOST,
        port=settings.SOCKET_IO_PORT,
        reload=True,
        log_level="info",
        ws_max_size=16 * 1024 * 1024,  # 16MB max WebSocket message size
        forwarded_allow_ips="*",  # Allow forwarded requests
        access_log=True
    )
