import logging
import uvicorn
from fastapi import FastAPI

from app.core.service_connector import ServiceConnector
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Create Socket.IO service connector
socket_connector = ServiceConnector("socket-io", settings.SOCKET_IO_URL)

# Add API routers if needed
# app.include_router(api_router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await socket_connector.initialize()
        logger.info("Socket.IO service started successfully")
    except Exception as e:
        logger.error(f"Error starting Socket.IO service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    try:
        await socket_connector.shutdown()
        logger.info("Socket.IO service shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down Socket.IO service: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def start():
    """Start the Socket.IO service"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    start()
