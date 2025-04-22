"""
Main application module for the socket-io service.
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

from app.core.socket_server import SocketServer
from app.core.presence_manager import PresenceManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "user": os.getenv("PG_USER", "?"),
    "password": os.getenv("PG_PASSWORD", "?"),
    "host": os.getenv("PG_HOST", "?"),
    "database": os.getenv("PG_DATABASE", "?"),
    "port": int(os.getenv("PG_PORT", "5432")),
}

# Create FastAPI app
app = FastAPI(title="Socket.IO Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create socket server
socket_server = SocketServer()

# Create presence manager
presence_manager = PresenceManager(
    socket_server,
    {
        "postgres": DB_CONFIG,
        "rabbitmq": {
            "url": os.getenv(
                "RABBITMQ_URL",
                "amqp://guest:guest@localhost:5672/"
            )
        }
    }
)

# Initialize database pool
db_pool = None


async def setup_database():
    """Initialize database connection pool"""
    global db_pool
    logger.info("Connecting to PostgreSQL database...")
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("Database connection established")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Socket.IO service...")

    # Setup database connection
    await setup_database()

    # Initialize socket server
    await socket_server.initialize()

    # Initialize presence manager
    await presence_manager.initialize()

    logger.info("Socket.IO service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Socket.IO service...")

    # Shutdown presence manager
    await presence_manager.shutdown()

    # Shutdown socket server
    await socket_server.shutdown()

    # Close database connection
    if db_pool:
        await db_pool.close()

    logger.info("Socket.IO service shut down successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Mount Socket.IO app
app.mount("/", socket_server.app)
