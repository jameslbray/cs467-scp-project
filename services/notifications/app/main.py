"""
Main application module for the notification service.
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..app.core.notification_manager import NotificationManager
from ..app.core.config import settings
from .api.routers import router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Notification Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix=settings.API_PREFIX)

# Create presence manager
notification_manager = NotificationManager(
    {
        "rabbitmq": {
            "url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
        },
        "postgres": {
            "user": os.getenv("PRESENCE_POSTGRES_USER", "postgres"),
            "password": os.getenv("PRESENCE_POSTGRES_PASSWORD", "postgres"),
            "host": os.getenv("PRESENCE_POSTGRES_HOST", "postgres_db"),
            "database": os.getenv("PRESENCE_POSTGRES_DB", "sycolibre"),
            "port": int(os.getenv("PRESENCE_POSTGRES_PORT", "5432")),
        },
    }
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Notification service...")

    # Initialize notification manager
    await notification_manager.initialize()

    logger.info("Notification service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down notification service...")

    # Shutdown presence manager
    await notification_manager.shutdown()

    logger.info("Notification service shut down successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
