#!/usr/bin/env python3
"""
Main Socket.IO server for SycoLibre
Handles real-time messaging and integrates with the presence service
"""

import os
import asyncio
from dotenv import load_dotenv
# import json
# from datetime import datetime
import asyncpg
import socketio
import uvicorn
import logging

# Import the presence service components
from services.presence.manager import PresenceManager
from services.presence.websocket import SocketManager
from utils.utils import CustomJSON
from motor.motor_asyncio import AsyncIOMotorClient
# from services.presence.models import UserStatus, StatusType

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection properties
DB_CONFIG = {
    "user": os.getenv("PG_USER", "?"),
    "password": os.getenv("PG_PASSWORD", "?"),
    "host": os.getenv("PG_HOST", "?"),
    "database": os.getenv("PG_DATABASE", "?"),
    "port": int(os.getenv("PG_PORT", "5432")),
}

logger.info(f"DB_CONFIG: {DB_CONFIG}")

# MongoDB connection properties
MONGO_URL = "mongodb://username:password@ip:27017/scp-db"
mongo_client = AsyncIOMotorClient(MONGO_URL)
mongo_db = mongo_client["scp-db"]
messages_collection = mongo_db["messages"]

# Create a new Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:5173",  # Explicitly allow React app
        "*"
        ],
    json=CustomJSON,
    logger=True
)

# Create socket app
app = socketio.ASGIApp(sio)

# Initialize database pool
db_pool = None

# Create socket manager for presence service
socket_manager = SocketManager(sio)

# Initialize presence manager
presence_manager = None

# Full config including Redis and RabbitMQ for presence service
config = {
    "postgres": DB_CONFIG,
    # "redis": {
    #     "host": os.getenv("REDIS_HOST", "localhost"),
    #     "port": int(os.getenv("REDIS_PORT", "6379")),
    #     "password": os.getenv("REDIS_PASSWORD", "")
    # },
    "rabbitmq": {
        "url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    }
}


async def setup_database():
    """Initialize database connection pool"""
    global db_pool
    logger.info("Connecting to PostgreSQL database...")
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("Database connection established")


async def startup():
    """Initialize services and connections"""
    global presence_manager

    # Setup database connection
    await setup_database()

    # Initialize presence manager
    logger.info("Starting presence service...")
    presence_manager = PresenceManager(socket_manager, config)
    await presence_manager.initialize()
    logger.info("Presence service started")


async def shutdown():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down server...")

    # Close presence manager
    if presence_manager:
        await presence_manager.close()

    # Close database connection
    if db_pool:
        await db_pool.close()

    logger.info("Server shutdown complete")


@sio.event
async def connect(sid: str, environ, auth: dict = None):
    """Handle new socket connection"""
    logger.info(f"New client connected: {sid}. Auth received: {auth}")

    if auth:
        # Assuming client sends {'userId': 'some_id'} in auth
        user_id = auth.get("userId")
        if user_id:
            logger.info(f"Authenticated user {user_id} for sid {sid}")
            if presence_manager:
                # Pass the extracted user_id to the presence manager
                await presence_manager.handle_connect(sid, auth)
        else:
            logger.warning(f"Auth data received for {sid} but missing 'userId'.")
            # Consider disconnecting if userId is mandatory
            # await sio.disconnect(sid)
    else:
        logger.warning(f"Connection attempt from {sid} without auth data.")
        # Consider disconnecting if auth is mandatory
        # await sio.disconnect(sid)

@sio.event
async def send_message(sid, data):
    """Handle new message and save to MongoDB (async with motor)"""
    try:
        logger.info(f"Received message: {data}")

        required_fields = ['sender_id', 'room_id', 'recipient_ids', 'content', 'timestamp']
        if not all(k in data for k in required_fields):
            logger.warning("Missing required fields")
            return

        await messages_collection.insert_one({
            "sender_id": data["sender_id"],
            "room_id": data["room_id"],
            "recipient_ids": data["recipient_ids"],
            "content": data["content"],
            "timestamp": data["timestamp"],
            "has_emoji": data.get("has_emoji", False)
        })

        await sio.emit("chat_message", data, room=data["room_id"])
        logger.info(f"Message stored and sent to room {data['room_id']}")

    except Exception as e:
        logger.error(f"Error saving message to MongoDB: {e}")

@sio.event
async def fetch_recent_messages(sid, data):
    room_id = data.get("room_id")
    if not room_id:
        logger.warning("No room_id provided")
        return

    messages_cursor = messages_collection.find(
        {"room_id": room_id}
    ).sort("timestamp", -1).limit(10)

    messages = await messages_cursor.to_list(length=10)
    messages.reverse()
    for msg in messages:
        if "_id" in msg:
            msg["_id"] = str(msg["_id"])
    await sio.emit("recent_messages", {"messages": messages}, to=sid)

@sio.event
async def join_room(sid, data):
    room = data.get("room")
    if room:
        await sio.enter_room(sid, room) 
        logger.info(f"Client {sid} joined room {room}")


# @sio.event
# async def send_message(sid, data):
#     """Handle new message and save to database"""
#     user = data.get("user")
#     text = data.get("text")
#     room = data.get("room")
#     timestamp = data.get("timestamp")

#     try:
#         # Save message to PostgreSQL database
#         await db_pool.execute(
#             'INSERT INTO chat_messages (user_name, text, room, timestamp)
#               VALUES ($1, $2, $3, $4)',
#             user, text, room, timestamp
#         )

#         # Broadcast message to all users in the room
#         await sio.emit("chat_message", data, room=room)

#         logger.info(f"Message from {user} in room {room}: {text}")
#     except Exception as e:
#         logger.error(f"DB insert error: {e}")


@sio.event
async def disconnect(sid):
    """Handle socket disconnection"""
    logger.info(f"Client disconnected: {sid}")

    # This will be handled by the presence manager if needed
    if presence_manager:
        # Let the presence manager handle the disconnection logic
        user_id = await presence_manager.handle_disconnect(sid)
        if user_id:
            logger.info(f"User {user_id} associated with "
                        "{sid} is now offline.")

# @sio.event
# async def message(sid, data):
#     """Handle incoming messages"""
#     logger.info(f"Message from {sid}: {data}")

#     # You can handle different message types here
#     # For example, if you want to handle a specific event:
#     if data.get("event") == "presence:request_friend_statuses":
#         await presence_request_friend_statuses(sid, data)
#     # elif data.get("event") == "presence:request_friend_statuses":
#     #     await presence_request_friend_statuses(sid, data)


@sio.event
async def presence_request_friend_statuses(sid: str, data: dict = None):
    """Handle request for friend statuses from a client."""
    # Assuming the user ID was stored during connection/authentication
    user_id = presence_manager.socket_manager.get_user_id_from_sid(sid)
    if user_id:
        logger.info(
            (
                f"Received presence_request_friend_statuses from {sid} "
                f"for user {user_id}"
            )
        )
        # TODO: Implement logic to fetch friend statuses
        # For now, just send a mock response
        await presence_manager.send_friend_statuses(user_id, sid)
    else:
        logger.warning(f"Could not find user_id for sid {sid} to send"
                       "friend statuses.")


@sio.event
async def presence_update_status(sid: str, data: dict):
    """"Handle presence update status from a client."""
    user_id = presence_manager.socket_manager.get_user_id_from_sid(sid)
    if user_id:
        status = data.get("status")
        logger.info(f"Received presence_update_status from {sid} for user "
                    "{user_id} with status {status}")
        await presence_manager.update_user_status(user_id, status)
    else:
        logger.warning(f"Could not find user_id for sid {sid} to update "
                       "status.")


async def main():
    """Main entry point"""
    # Initialize services
    await startup()

    # Run the Socket.IO server
    config = uvicorn.Config(app, host="0.0.0.0", port=3001, log_level="info")
    server = uvicorn.Server(config)

    # Handle graceful shutdown
    try:
        await server.serve()
    finally:
        await shutdown()


if __name__ == "__main__":
    # Run the server
    logger.info("Starting SycoLibre Socket.IO server...")
    logger.info("http://localhost:3001")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
