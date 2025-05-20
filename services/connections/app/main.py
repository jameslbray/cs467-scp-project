"""
Main application module for the connection service.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.connection_manager import ConnectionManager
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
connection_manager = ConnectionManager(
    {
        "rabbitmq": {
            "url": settings.RABBITMQ_URL
        },
        "postgres": {
            "user": settings.POSTGRES_USER,
            "password": settings.POSTGRES_PASSWORD,
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB
        },
    }
)

# Define the lifespan handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Connection service...")

    # Initialize notification manager
    await connection_manager.initialize()
    # await rabbitmq_client.connect()
    # logger.info("RabbitMQ connection established")
    logger.info("Connection service started successfully")

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down Connection Service")
    await connection_manager.shutdown()

    logger.info("Connection service shut down successfully")
    # await rabbitmq_client.close()
    # logger.info("RabbitMQ connection closed")

# Create FastAPI app
app = FastAPI(
    title="Connection Service",
    description="Service for managing Connections",
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
