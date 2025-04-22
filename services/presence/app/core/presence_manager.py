"""
Presence manager for handling WebSocket connections and user presence state.
"""

import logging
import json
import aio_pika
from typing import Dict, Any, Optional
from datetime import datetime
import socketio

# Configure logging
logger = logging.getLogger(__name__)


class PresenceManager:
    """Manages user presence and WebSocket connections."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the presence manager.

        Args:
            config: Configuration dictionary containing RabbitMQ and other settings
        """
        self.config = config
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self._initialized = False

        # Initialize Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=["*"],  # Configure as needed
            logger=True
        )
        self.app = socketio.ASGIApp(self.sio)

        # User presence data
        self.presence_data: Dict[str, Dict[str, Any]] = {}
        self.sid_to_user: Dict[str, str] = {}  # sid -> user_id mapping
        self.user_to_sid: Dict[str, str] = {}  # user_id -> sid mapping

        # Register Socket.IO event handlers
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('presence:request_friend_statuses',
                    self._handle_friend_statuses_request)

    async def initialize(self) -> None:
        """Initialize the presence manager."""
        if self._initialized:
            return

        # Connect to RabbitMQ
        await self._connect_rabbitmq()

        logger.info("Presence manager initialized")
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the presence manager."""
        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()

        logger.info("Presence manager shut down")

    async def _connect_rabbitmq(self) -> None:
        """Connect to RabbitMQ."""
        try:
            # Connect to RabbitMQ
            self.rabbitmq_connection = await aio_pika.connect_robust(
                self.config["rabbitmq"]["url"]
            )

            # Create a channel
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()

            # Declare exchange
            await self.rabbitmq_channel.declare_exchange(
                "presence",
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            # Declare queue
            queue = await self.rabbitmq_channel.declare_queue(
                "presence_updates",
                durable=True
            )

            # Bind queue to exchange
            await queue.bind("presence", routing_key="presence_updates")

            # Start consuming messages
            await queue.consume(self._process_presence_message)

            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def _process_presence_message(self, message: aio_pika.IncomingMessage) -> None:
        """Process a presence message from RabbitMQ."""
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())
                user_id = body.get("user_id")
                status = body.get("status")

                if user_id and status:
                    # Update user status
                    await self._update_user_status(user_id, status)
            except Exception as e:
                logger.error(f"Error processing presence message: {e}")

    async def _update_user_status(self, user_id: str, status: str) -> None:
        """Update a user's status and notify relevant clients."""
        if user_id in self.presence_data:
            self.presence_data[user_id].update({
                "status": status,
                "last_seen": datetime.now().timestamp()
            })

            # Notify all clients about the status update
            await self.sio.emit(
                "presence:status_update",
                {
                    "user_id": user_id,
                    "status": status
                }
            )

    async def _on_connect(self, sid: str, environ: Dict[str, Any]) -> None:
        """Handle new socket connection."""
        logger.info(f"New client connected: {sid}")

        # Extract user ID from authorization header if present
        auth_data = environ.get("HTTP_AUTHORIZATION", "")
        if auth_data:
            user_id = auth_data  # In production, validate the token
            self.register_user(sid, user_id)
            await self._publish_presence_update(user_id, "online")
            logger.info(f"User {user_id} connected with sid {sid}")

    async def _on_disconnect(self, sid: str) -> None:
        """Handle socket disconnection."""
        logger.info(f"Client disconnected: {sid}")

        user_id = self.unregister_user(sid)
        if user_id:
            await self._publish_presence_update(user_id, "offline")
            logger.info(f"User {user_id} disconnected")

    async def _handle_friend_statuses_request(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle a request for friend statuses."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.warning(f"Could not find user_id for sid {sid}")
            return

        # In a real implementation, you would fetch friend statuses from a database
        # For this example, we'll just send a dummy response
        await self.sio.emit(
            "presence:friend_statuses",
            {
                "friends": [
                    {"user_id": "friend1", "status": "online"},
                    {"user_id": "friend2", "status": "offline"}
                ]
            },
            room=sid
        )

    def register_user(self, sid: str, user_id: str) -> None:
        """Register a user with a socket ID."""
        self.sid_to_user[sid] = user_id
        self.user_to_sid[user_id] = sid
        self.presence_data[user_id] = {
            "status": "online",
            "last_seen": datetime.now().timestamp(),
            "sid": sid
        }

    def unregister_user(self, sid: str) -> Optional[str]:
        """Unregister a user with a socket ID."""
        user_id = self.sid_to_user.get(sid)
        if user_id:
            del self.sid_to_user[sid]
            if user_id in self.user_to_sid:
                del self.user_to_sid[user_id]
            if user_id in self.presence_data:
                self.presence_data[user_id].update({
                    "status": "offline",
                    "last_seen": datetime.now().timestamp(),
                    "sid": None
                })
        return user_id

    def get_user_id_from_sid(self, sid: str) -> Optional[str]:
        """Get user ID from socket ID."""
        return self.sid_to_user.get(sid)

    def get_sid_from_user_id(self, user_id: str) -> Optional[str]:
        """Get socket ID from user ID."""
        return self.user_to_sid.get(user_id)

    async def _publish_presence_update(self, user_id: str, status: str) -> None:
        """Publish a presence update to RabbitMQ."""
        if not self.rabbitmq_channel:
            logger.warning("RabbitMQ channel not available")
            return

        try:
            # Create message
            message = aio_pika.Message(
                body=json.dumps({
                    "user_id": user_id,
                    "status": status
                }).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            # Publish message
            await self.rabbitmq_channel.default_exchange.publish(
                message,
                routing_key="presence_updates"
            )

            logger.info(
                f"Published presence update for user {user_id}: {status}")
        except Exception as e:
            logger.error(f"Failed to publish presence update: {e}")

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current status."""
        presence_data = self.presence_data.get(user_id, {})
        return {
            "status": presence_data.get("status", "offline"),
            "last_seen": presence_data.get("last_seen", 0)
        }

    def set_user_status(self, user_id: str, status: str) -> bool:
        """Set user's status."""
        if user_id not in self.presence_data:
            return False

        self.presence_data[user_id].update({
            "status": status,
            "last_seen": datetime.now().timestamp()
        })

        logger.info(f"User {user_id} status set to {status}")
        return True
