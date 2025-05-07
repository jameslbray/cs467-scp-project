import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..core.config import get_settings

logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None
db: Optional[AsyncIOMotorDatabase[Dict[str, Any]]] = None


async def init_mongo() -> None:
    """Initialize MongoDB connection."""
    global client, db
    settings = get_settings()
    try:
        logger.info("Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        # Verify connection
        await db.command("ping")
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    if client is not None:
        client.close()
        logger.info("MongoDB connection closed")


def get_db() -> Optional[AsyncIOMotorDatabase[Dict[str, Any]]]:
    """Get database instance."""
    if db is None:
        raise RuntimeError("MongoDB not initialized")
    return db
