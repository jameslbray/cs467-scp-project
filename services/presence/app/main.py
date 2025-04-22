from app.api.routers import router as api_router
import logging
import asyncio
import uvicorn
from typing import Dict, List, Optional, Any
from fastapi import FastAPI

from app.core.socket_client import SocketClient
from app.core.presence_manager import PresenceManager
from app.core.config import settings, get_socket_io_client_config

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Create socket client and presence manager instances
socket_client = None
presence_manager = None

# Add routes


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {
        "message": "Welcome to the Presence Service API",
        "service": "presence-service",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}

# Include API routers (after app creation)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup():
    """Initialize services and connections on startup."""
    global socket_client, presence_manager

    logger.info("Starting presence service...")

    # Initialize socket client with connection to socket-io service
    socket_io_config = get_socket_io_client_config()
    socket_client = SocketClient(socket_io_config["url"])
    await socket_client.initialize()

    # Initialize presence manager
    presence_manager = PresenceManager(socket_client, {})
    await presence_manager.initialize()

    logger.info("Presence service started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    global presence_manager, socket_client

    logger.info("Shutting down presence service...")

    if presence_manager:
        await presence_manager.close()

    if socket_client:
        await socket_client.shutdown()

    logger.info("Presence service shutdown complete")
