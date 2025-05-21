"""
Main application module for the presence service.
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ..app.core.presence_manager import PresenceManager
from ..app.core.config import settings
from .api.routers import router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create presence manager
presence_manager = PresenceManager(
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

    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Notification service...")

    # Initialize notification manager
    await presence_manager.initialize()
    logger.info("Presence service started successfully")

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down Presence Service")
    await presence_manager.shutdown()

    logger.info("Presence service shut down successfully")


# Create FastAPI app
app = FastAPI(
    title="Presence Service",
    description="Service for managing user presence",
    version="0.1.0",
    lifespan=lifespan,
)

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

