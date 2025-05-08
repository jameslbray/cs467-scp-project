import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.shared.utils.retry import CircuitBreaker, with_retry

from .core.rabbitmq import ChatRabbitMQClient
from .core.socket_connector import SocketManager
from .db.mongo import close_mongo_connection, get_db, init_mongo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
socket_connector = SocketManager()
rabbitmq_client = ChatRabbitMQClient()

# Circuit breaker configurations
mongo_circuit_breaker = CircuitBreaker(
    name="mongo-connection",
    failure_threshold=3,
    reset_timeout=5
)

rabbitmq_circuit_breaker = CircuitBreaker(
    name="rabbitmq-connection",
    failure_threshold=3,
    reset_timeout=5
)

socket_circuit_breaker = CircuitBreaker(
    name="socket-connection",
    failure_threshold=3,
    reset_timeout=5,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events
    """
    # Startup logic with circuit breaker pattern
    logger.info("Starting chat service...")

    try:
        # Initialize MongoDB with retry and circuit breaker
        await with_retry(
            init_mongo,
            max_attempts=5,
            max_delay=1,
            exponential_base=2,
            circuit_breaker=mongo_circuit_breaker,
            operation_args=(),
            operation_kwargs={}  # Any parameters for init_mongo would go here
        )
        logger.info("MongoDB connection established")

        # Initialize the socket connector with retry and circuit breaker
        await with_retry(
            socket_connector.initialize,
            max_attempts=5,
            max_delay=1,
            exponential_base=2,
            circuit_breaker=socket_circuit_breaker
        )
        logger.info("Socket connector initialized")

        # Initialize RabbitMQ client with retry and circuit breaker
        await with_retry(
            rabbitmq_client.initialize,
            max_attempts=5,
            max_delay=1,
            exponential_base=2,
            circuit_breaker=rabbitmq_circuit_breaker
        )
        logger.info("RabbitMQ client initialized")

        logger.info("Chat service started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Still proceed with starting the app, but some services might be unavailable
        logger.warning("Chat service started with degraded functionality")

    yield  # FastAPI serves requests during this period

    # Shutdown logic
    logger.info("Shutting down chat service...")

    # Close all connections in reverse order, with graceful error handling
    try:
        await socket_connector.shutdown()
        logger.info("Socket connector shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down socket connector: {e}")

    try:
        await rabbitmq_client.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {e}")

    try:
        await close_mongo_connection()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")

    logger.info("Chat service shutdown complete")

# Create FastAPI application with lifespan manager
app = FastAPI(
    title="Chat Service API",
    description="Service for managing chat and messaging",
    version="0.1.0",
    lifespan=lifespan,
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
    # Check the state of the circuit breakers
    status = "healthy"
    circuit_breakers = {
        "mongo": "closed" if not mongo_circuit_breaker.is_open else "open",
        "rabbitmq": "closed" if not rabbitmq_circuit_breaker.is_open else "open",
        "socket": "closed" if not socket_circuit_breaker.is_open else "open",
    }

    # If any circuit breaker is open, consider the service degraded
    if any(state == "open" for state in circuit_breakers.values()):
        status = "degraded"

    return {
        "status": status,
        "circuit_breakers": circuit_breakers
    }


@app.get("/test-mongo")
async def test_mongo_connection():
    """Test MongoDB connection and list collections."""
    try:
        # Use circuit breaker for this test operation
        async def get_collections():
            database = get_db()
            return await database.list_collection_names()

        collections = await with_retry(
            get_collections,
            max_retries=2,
            delay=0.5,
            circuit_breaker=mongo_circuit_breaker
        )

        return {
            "status": "success",
            "message": "Successfully connected to MongoDB",
            "collections": collections,
            "database": get_db().name,
            "circuit_breaker": "closed" if not mongo_circuit_breaker.is_open else "open",
        }
    except RuntimeError as e:
        logger.error(f"MongoDB not initialized: {e}")
        return {"status": "error", "message": "MongoDB not initialized"}
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        return {"status": "error", "message": f"Failed to connect to MongoDB: {str(e)}"}
