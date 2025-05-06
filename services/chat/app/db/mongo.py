import logging

import motor.motor_asyncio

from ..core.config import Settings

logger = logging.getLogger(__name__)

client: motor.motor_asyncio.AsyncIOMotorClient = None
db: motor.motor_asyncio.AsyncIOMotorDatabase = None


async def init_mongo() -> None:
    """Initialize MongoDB connection."""
    global client, db
    try:
        logger.info("Connecting to MongoDB...")
        client = motor.motor_asyncio.AsyncIOMotorClient(Settings.MONGO_URI)
        db = client[Settings.MONGO_DB]
        # Verify connection
        await db.command("ping")
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global client
    if client is not None:
        client.close()
        logger.info("MongoDB connection closed")


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Get database instance."""
    if db is None:
        raise RuntimeError("MongoDB not initialized")
    return db
