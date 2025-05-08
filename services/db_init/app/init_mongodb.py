import asyncio
import logging
import os
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_mongodb():
    # Get configuration from environment variables
    mongo_user = os.getenv("MONGO_ADMIN_USER", "admin")
    mongo_password = os.getenv("MONGO_ADMIN_PASSWORD", "password")
    mongo_host = os.getenv("MONGO_HOST", "mongo_db")
    mongo_port = os.getenv("MONGO_PORT", "27017")
    db_name = os.getenv("MONGO_DB_NAME", "chat_db")

    # Build connection string with authentication
    mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{db_name}?authSource=admin"

    logger.info(f"Initializing MongoDB database: {db_name}")
    logger.info(f"mongo_uri: {mongo_uri}")

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_uri)

    try:
        # Verify connection
        await client.admin.command('ping')
        logger.info("Connected to MongoDB successfully")

        # Get or create the database
        db = client[db_name]

        # Create collections for the chat service
        collections = await db.list_collection_names()

        # Create message_logs collection if it doesn't exist
        if 'message_logs' not in collections:
            logger.info("Creating message_logs collection")
            await db.create_collection('message_logs')

        # Create rooms collection if it doesn't exist
        if 'rooms' not in collections:
            logger.info("Creating rooms collection")
            await db.create_collection('rooms')

            # Create a default General room
            room_result = await db.rooms.insert_one({
                "name": "General",
                "description": "Public chat room for everyone",
                "created_at": datetime.utcnow(),
                "is_private": False,
                "room_id": 1  # Numeric ID for the room
            })
            logger.info(f"Created default General room with ID: {room_result.inserted_id}")
        else:
            # Check if General room exists
            general_room = await db.rooms.find_one({"name": "General"})
            if not general_room:
                room_result = await db.rooms.insert_one({
                    "name": "General",
                    "description": "Public chat room for everyone",
                    "created_at": datetime.utcnow(),
                    "is_private": False,
                    "room_id": 1  # Numeric ID for the room
                })
                logger.info(f"Created default General room with ID: {room_result.inserted_id}")
            else:
                logger.info(f"General room already exists with ID: {general_room.get('_id')}")

        # Add a test message to the message_logs collection
        # Using the format from your message_log.py model
        test_message = {
            "_id": ObjectId(),  # Generate a new ObjectId
            "room_id": 1,       # ID of the General room
            "sender_id": 1,     # Example user ID
            "content": "Hello, this is a test message from the database initialization!",
            "timestamp": datetime.utcnow()
        }

        # Check if we already have test messages to avoid duplicates
        message_count = await db.message_logs.count_documents({})
        if message_count < 5:  # Only add if we have fewer than 5 messages
            message_result = await db.message_logs.insert_one(test_message)
            logger.info(f"Added test message with ID: {message_result.inserted_id}")

            # Add a few more sample messages for testing
            await db.message_logs.insert_many([
                {
                    "room_id": 1,
                    "sender_id": 2,
                    "content": "Welcome to the chat system!",
                    "timestamp": datetime.utcnow()
                },
                {
                    "room_id": 1,
                    "sender_id": 1,
                    "content": "Thanks! Excited to be here.",
                    "timestamp": datetime.utcnow()
                },
                {
                    "room_id": 1,
                    "sender_id": 3,
                    "content": "This is a great example of MongoDB integration.",
                    "timestamp": datetime.utcnow()
                }
            ])
            logger.info("Added additional sample messages")
        else:
            logger.info(f"Test messages already exist. Current count: {message_count}")

        # Create indexes for better performance
        logger.info("Creating indexes")
        await db.message_logs.create_index("room_id")
        await db.message_logs.create_index("timestamp")
        await db.rooms.create_index("name", unique=True)
        await db.rooms.create_index("room_id", unique=True)

        logger.info("MongoDB initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"MongoDB initialization error: {e}")
        return False
    finally:
        client.close()
        logger.info("MongoDB connection closed")

if __name__ == "__main__":
    # Run the MongoDB initialization
    success = asyncio.run(init_mongodb())
    if not success:
        logger.error("MongoDB initialization failed")
        exit(1)
