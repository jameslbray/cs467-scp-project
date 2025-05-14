"""
Main application module for the notification service.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.notification_manager import NotificationManager
from .core.config import get_settings
from .api.routers import router
# from .core.rabbitmq import NotificationRabbitMQClient

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
# rabbitmq_client = NotificationRabbitMQClient(settings=settings)


# Create presence manager
notification_manager = NotificationManager(
    {
        "rabbitmq": {
            "url": settings.RABBITMQ_URL or "amqp://guest:guest@rabbitmq:5672/"
        },
        "mongodb": {
            "user": settings.MONGO_USER or "admin",
            "password": settings.MONGO_PASSWORD or "password",
            "host": settings.MONGO_HOST or "mongo_db",
            "database": settings.MONGO_DB or "chat_db",
            "port": settings.MONGO_PORT or "27017",
        },
    }
)

# Define the lifespan handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Notification service...")

    # Initialize notification manager
    await notification_manager.initialize()
    # await rabbitmq_client.connect()
    # logger.info("RabbitMQ connection established")
    logger.info("Notification service started successfully")

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down User Service")
    await notification_manager.shutdown()

    logger.info("Notification service shut down successfully")
    # await rabbitmq_client.close()
    # logger.info("RabbitMQ connection closed")

# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Service for managing notifications",
    version="0.1.0",
    lifespan=lifespan,
)

# app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(router, prefix=settings.API_PREFIX)
# app.state.limiter = limiter

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# if __name__ == "__main__":
#     import uvicorn

#     # Load environment variables from .env file
#     load_dotenv()

#     # Run the application with Uvicorn
#     uvicorn.run(
#         app,
#         host="localhost",
#         port=8025,
#         log_level=settings.LOG_LEVEL.lower()
#     )
