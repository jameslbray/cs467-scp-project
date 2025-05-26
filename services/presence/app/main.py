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
from .core.presence_rabbitmq import PresenceRabbitMQClient
from ..app.core.config import settings
from .api.routers import router


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Notification service...")
    app.state.rabbitmq_client = PresenceRabbitMQClient()
    # Initialize notification manager
    app.state.presence_manager = PresenceManager(
        {
            "postgres": {
                "user": settings.POSTGRES_USER,
                "password": settings.POSTGRES_PASSWORD,
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
                "database": settings.POSTGRES_DB
            },
        },
        rabbitmq_client=app.state.rabbitmq_client
    )
    await app.state.presence_manager.initialize()   
    await app.state.rabbitmq_client.initialize()
    
    logger.info("Presence service started successfully")

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down Presence Service")
    await app.state.presence_manager.shutdown()
    await app.state.rabbitmq_client.shutdown()

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

