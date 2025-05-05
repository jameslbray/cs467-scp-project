"""
Main application module for the socket-io service.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

# import socketio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.presence.app.core.presence_manager import PresenceManager
from services.rabbitmq.core.client import RabbitMQClient
from services.rabbitmq.core.config import Settings as RabbitMQSettings
from services.shared.utils.retry import CircuitBreaker, with_retry
from services.socket_io.app.core.socket_server import SocketServer

from .core.config import get_settings
from .core.events import AuthEvents

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create socket server
socket_server = SocketServer()

# Create presence manager with only RabbitMQ configuration
presence_manager = PresenceManager(
    {
        "rabbitmq": {
            "url": os.getenv(
                "RABBITMQ_URL",
                "?"
            )
        }
    },
    # socket_server=socket_server
)

# Initialize circuit breaker for presence manager
presence_circuit_breaker = CircuitBreaker(
    "presence_manager",
    failure_threshold=3,
    reset_timeout=30.0  # Reduced timeout for faster recovery
)

# Get settings
settings = get_settings()
rabbitmq_settings = RabbitMQSettings(RABBITMQ_URL=os.getenv("RABBITMQ_URL"))

# Create RabbitMQ client
rabbitmq = RabbitMQClient(rabbitmq_settings)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.SOCKET_IO_CORS_ALLOWED_ORIGINS
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events handler with resilient initialization."""
    # Startup
    logger.info("Starting Socket.IO service...")

    try:
        await with_retry(
            socket_server.initialize,
            max_attempts=5,
            initial_delay=5.0,
            max_delay=60.0
        )
    except Exception as e:
        logger.error(f"Failed to fully initialize socket server: {e}")
        # Continue anyway - the socket server has its own retry logic

    initialization_complete = False
    max_init_attempts = 3

    for attempt in range(max_init_attempts):
        try:
            if not initialization_complete and not presence_manager._initialized:
                await with_retry(
                    presence_manager.initialize,
                    max_attempts=3,
                    initial_delay=5.0,
                    max_delay=30.0,
                    circuit_breaker=presence_circuit_breaker
                )
                initialization_complete = True
                logger.info("Presence manager initialized successfully")
                break
        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1}/{max_init_attempts} to initialize "
                f"presence manager failed: {e}"
            )
            await asyncio.sleep(5.0)  # Wait before next attempt

    # Mount socket.io routes
    app.mount("/socket.io", socket_server.app)
    logger.info(
        "Socket.IO service started (some components may initialize later)"
    )

    # Connect to RabbitMQ
    await rabbitmq.connect()

    # Set up auth exchange
    await rabbitmq.declare_exchange("auth", exchange_type="topic")

    # Initialize auth events
    global auth_events
    auth_events = AuthEvents(sio, rabbitmq)

    yield

    # Shutdown
    logger.info("Shutting down Socket.IO service...")
    await presence_manager.shutdown()
    await socket_server.shutdown()
    logger.info("Socket.IO service shut down successfully")

    # Close RabbitMQ connection
    await rabbitmq.close()

# Create FastAPI app
app = FastAPI(title="Socket.IO Service", lifespan=lifespan)

# Create ASGI app by wrapping Socket.IO
# socket_app = socketio.ASGIApp(sio, app)

# Initialize auth events
auth_events = None

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


@app.get("/health")
async def health_check():
    """Health check endpoint with component status."""
    status = {
        "service": "healthy",
        "components": {
            "socket_server": (
                "initialized"
                if socket_server._initialized
                else "initializing"
            ),
            "presence_manager": (
                "initialized"
                if presence_manager._initialized
                else "initializing"
            ),
        }
    }
    return status


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    await rabbitmq.close()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:socket_app",
        host=settings.SOCKET_IO_HOST,
        port=settings.SOCKET_IO_PORT,
        reload=True
    )
