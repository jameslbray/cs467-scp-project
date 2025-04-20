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

# Create a new Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:5173",  # Explicitly allow React app
        "*"
        ],
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
async def connect(sid, environ):
    """Handle new socket connection"""
    logger.info(f"New client connected: {sid}")

    # TODO: Do we need to auth here?
    # If you need to authenticate before allowing connection:
    auth_data = environ.get("HTTP_AUTHORIZATION", "")
    if presence_manager:
        await presence_manager.handle_connect(sid, {"userId": auth_data})


# @sio.event
# async def join_room(sid, room):
#     """Handle room join request"""
#     sio.enter_room(sid, room)
#     logger.info(f"Client {sid} joined room {room}")


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
#             'INSERT INTO chat_messages (user_name, text, room, timestamp) VALUES ($1, $2, $3, $4)',
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
            logger.info(f"User {user_id} associated with {sid} is now offline.")


@sio.event(namespace='/')  # Ensure it's in the default namespace unless
# specified otherwise
async def presence_request_friend_statuses(sid, data):
    """Handle request for friend statuses from a client."""
    # Assuming the user ID was stored during connection/authentication
    # This part needs refinement based on how you store the user_id associated
    # with the sid
    user_id = presence_manager.socket_manager.get_user_id_from_sid(sid)
    # You'll need to implement get_user_id_from_sid
    if user_id and presence_manager:
        logger.info(f"Received presence:request_friend_statuses from {sid} "
                    "for user {user_id}")
        await presence_manager.send_friend_statuses(user_id, sid)
    else:
        logger.warning(f"Could not find user_id for sid {sid} to send"
                       "friend statuses.")


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
