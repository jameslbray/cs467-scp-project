# services/chat/app/main.py

from app.db.mongo import init_mongo, close_mongo_connection, get_db
from app.core.socket_connector import SocketManager
from app.core.rabbitmq import ChatRabbitMQClient
from app.api.routers import router as api_router
import logging
from fastapi import FastAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI application
app = FastAPI(
    title="Chat Service API",
    description="Service for managing chat and messaging",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {
        "message": "Welcome to the Chat Service API",
        "service": "chat-service",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}


@app.get("/test-mongo")
async def test_mongo_connection():
    """Test MongoDB connection and list collections."""
    try:
        database = get_db()  # This will raise an error if db is None
        # Try to list collections to verify connection
        collections = await database.list_collection_names()
        return {
            "status": "success",
            "message": "Successfully connected to MongoDB",
            "collections": collections,
            "database": database.name,
        }
    except RuntimeError as e:
        logger.error(f"MongoDB not initialized: {e}")
        return {"status": "error", "message": "MongoDB not initialized"}
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        return {"status": "error", "message": f"Failed to connect to MongoDB: {str(e)}"}


# Include routers
app.include_router(api_router, prefix="/api")

# Initialize services
socket_connector = SocketManager()
rabbitmq_client = ChatRabbitMQClient()


@app.on_event("startup")
async def startup():
    """Initialize services and connections"""
    logger.info("Starting chat service...")
    await init_mongo()
    # Initialize the socket connector
    await socket_connector.initialize()
    # Initialize RabbitMQ client
    await rabbitmq_client.initialize()
    logger.info("Chat service started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down chat service...")
    # Shutdown the socket connector
    await socket_connector.shutdown()
    # Close RabbitMQ connection
    await rabbitmq_client.close()
    await close_mongo_connection()
    logger.info("Chat service shutdown complete")


# Register additional event handlers if needed
# These event handlers are now managed in the SocketService class
# Add any custom message handlers here if they're not in the SocketService
