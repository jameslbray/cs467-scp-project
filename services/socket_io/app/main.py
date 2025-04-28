"""
Main application module for the socket-io service.
"""

import logging
import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.socket_io.app.core.socket_server import SocketServer
from services.presence.app.core.presence_manager import PresenceManager
from services.shared.utils.retry import CircuitBreaker, with_retry

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
    socket_server=socket_server
)

# Initialize circuit breaker for presence manager
presence_circuit_breaker = CircuitBreaker(
    "presence_manager",
    failure_threshold=3,
    reset_timeout=30.0  # Reduced timeout for faster recovery
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

    yield

    # Shutdown
    logger.info("Shutting down Socket.IO service...")
    await presence_manager.shutdown()
    await socket_server.shutdown()
    logger.info("Socket.IO service shut down successfully")


# Create FastAPI app
app = FastAPI(title="Socket.IO Service", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
