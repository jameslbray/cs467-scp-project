import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.types import ExceptionHandler

from services.shared.utils.security_headers import SecurityHeadersMiddleware

from .api.routers import router as api
from .core.config import get_settings
from .core.rabbitmq import UserRabbitMQClient

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)

# Get logger for this file
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# Get settings
settings = get_settings()
logger.info("Application settings loaded")

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "profile_pics")
os.makedirs(STATIC_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up User Service")
    await app.state.rabbitmq_client.connect()
    logger.info("RabbitMQ connection established")

    # Mount static files for profile pictures
    app.mount(
        "/static",
        StaticFiles(
            directory=os.path.join(os.path.dirname(__file__), "static")
        ),
        name="static",
    )

    yield  # This is where FastAPI serves requests

    # Shutdown logic
    logger.info("Shutting down User Service")
    await app.state.rabbitmq_client.close()
    logger.info("RabbitMQ connection closed")


# Create FastAPI application with lifespan handler
app = FastAPI(
    title="User Service API",
    description="Service for managing user authentication and profiles",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.rabbitmq_client = UserRabbitMQClient(settings=settings)

app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded, cast(ExceptionHandler, _rate_limit_exceeded_handler)
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api)
