import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

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
    now = datetime.now(timezone.utc).isoformat()

    # Build connection string with authentication
    mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{db_name}?authSource=admin"

    logger.info(f"Initializing MongoDB database: {db_name}")
    logger.info(f"mongo_uri: {mongo_uri}")

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_uri)

    try:
        # Verify connection
        await client.admin.command("ping")
        logger.info("Connected to MongoDB successfully")

        # Get or create the database
        db = client[db_name]

        # Create collections for the chat service
        collections = await db.list_collection_names()

        # Create rooms collection if it doesn't exist
        if "rooms" not in collections:
            logger.info("Creating rooms collection")
            await db.create_collection("rooms")

        # Create message collection if it doesn't exist
        if "messages" not in collections:
            logger.info("Creating messages collection")
            await db.create_collection("messages")

        # Create a default General room if it doesn't exist
        general_room = await db.rooms.find_one({"name": "General"})
        if not general_room:
            room_id = str(uuid.uuid4())
            room_doc = {
                "_id": room_id,
                "name": "General",
                "description": "Public chat room for everyone",
                "is_private": False,
                "created_at": now,
                "updated_at": now,
                "created_by": None,
                "participant_ids": [],
                "max_participants": None,
            }
            await db.rooms.insert_one(room_doc)
            logger.info(f"Created default General room with ID: {room_id}")
        else:
            logger.info(
                f"General room already exists with ID: {general_room.get('_id')}"
            )

        # Add a test message to the messages collection only if it is empty
        general_room = await db.rooms.find_one({"name": "General"})
        if general_room:
            room_id = general_room["_id"]
            message_count = await db.messages.count_documents({})
            if message_count == 0:
                now = datetime.now(timezone.utc).isoformat()
                test_users = [
                        {
                            "id": "11111111-1111-1111-1111-111111111111",
                            "username": "test_user",
                        },
                        {
                            "id": "22222222-2222-2222-2222-222222222222",
                            "username": "test_user2",
                        },
                    ]
                test_messages = [
                    {
                        "_id": str(uuid.uuid4()),
                        "room_id": room_id,
                        "sender_id": test_users[0]["id"],
                        "content": f"Hello from {test_users[0]['username']}! Welcome to the chat system!",
                        "created_at": now,
                        "updated_at": now,
                        "is_edited": False,
                    },
                    {
                        "_id": str(uuid.uuid4()),
                        "room_id": room_id,
                        "sender_id": test_users[1]["id"],
                        "content": f"Welcome from {test_users[1]['username']}! I hope you're having a great day.",
                        "created_at": now,
                        "updated_at": now,
                        "is_edited": False,
                    },
                ]
                await db.messages.insert_many(test_messages)
                logger.info("Added sample messages to the General room")
            else:
                logger.info(
                    f"Test messages already exist for General room. Current count: {message_count}"
                )

        # Create indexes for better performance
        logger.info("Creating indexes")
        await db.messages.create_index("room_id")
        await db.messages.create_index("created_at")
        await db.rooms.create_index("name", unique=True)

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
