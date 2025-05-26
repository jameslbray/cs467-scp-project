"""
Main application module for the notification service.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.notification_manager import NotificationManager
from .core.notification_rabbitmq import NotificationRabbitMQClient
from .core.config import get_settings
from .api.routers import router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
# limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# Get settings
logger.info("Application settings loaded")

# Initialize RabbitMQ client
rabbitmq_client = NotificationRabbitMQClient()


# Create presence manager
notification_manager = NotificationManager(
    {
        "rabbitmq": {
            "url": settings.RABBITMQ_URL
        },
        "mongodb": {
            "user": settings.MONGO_USER,
            "password": settings.MONGO_PASSWORD,
            "host": settings.MONGO_HOST,
            "database": settings.MONGO_DB,
            "port": settings.MONGO_PORT,
            "uri": settings.mongo_uri
        },
    },
    rabbitmq_client=rabbitmq_client,
)

# Define the lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Notification service...")

    # Initialize notification manager
    await rabbitmq_client.initialize()
    await notification_manager.initialize()
    logger.info("NotificationRabbitMQ connection established")
    logger.info("Notification service started successfully")

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down notification Service")
    await notification_manager.shutdown()
    logger.info("Notification service shut down successfully")
    await rabbitmq_client.shutdown()
    logger.info("NotificationRabbitMQ connection closed")

# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Service for managing notifications",
    version="0.1.0",
    lifespan=lifespan,
)


# Include routers
app.include_router(router, prefix=settings.API_PREFIX)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

