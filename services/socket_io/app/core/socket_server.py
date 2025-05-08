import json
import logging
from datetime import datetime
from typing import Any, Dict, Never, Optional

import socketio

from services.rabbitmq.core.client import RabbitMQClient
from services.rabbitmq.core.config import Settings as RabbitMQSettings
from services.shared.utils.retry import CircuitBreaker, with_retry
from services.presence.app.core.presence_manager import PresenceManager

from .config import get_socket_io_config

# Configure logging
logger = logging.getLogger(__name__)


class SocketServer:
    """Socket.IO server implementation."""

    def __init__(self, rabbitmq_settings: RabbitMQSettings):
        """Initialize the Socket.IO server."""
        self.sio = socketio.AsyncServer(
            logger=True,
            **get_socket_io_config(),
        )
        self.app = socketio.ASGIApp(self.sio)
        self.sid_to_user: Dict[str, str] = {}  # sid -> user_id mapping
        self.user_to_sid: Dict[str, str] = {}  # user_id -> sid mapping
        self._initialized = False

        # Initialize RabbitMQ client with provided settings
        self.rabbitmq = RabbitMQClient(rabbitmq_settings)

        # Initialize circuit breakers
        self.rabbitmq_cb = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30
        )

        # Initialize presence manager
        self.presence_manager = PresenceManager({
            "rabbitmq": {
                "url": rabbitmq_settings.RABBITMQ_URL
            }
        })

        # Register event handlers
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("error", self._on_error)
        self.sio.on("chat_message", self._on_chat_message)
        self.sio.on("presence_update", self._on_presence_update)

    async def initialize(self) -> bool:
        """Initialize the Socket.IO server and its dependencies."""
        if self._initialized:
            logger.debug("Socket.IO server already initialized")
            return True

        try:
            # Initialize RabbitMQ client with retries
            await with_retry(
                self._initialize_rabbitmq,
                max_attempts=5,
                initial_delay=5.0,
                max_delay=60.0,
                circuit_breaker=self.rabbitmq_cb
            )

            # Initialize presence manager
            await with_retry(
                self.presence_manager.initialize,
                max_attempts=3,
                initial_delay=5.0,
                max_delay=30.0
            )

            logger.info("Socket.IO server initialized successfully")
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to fully initialize Socket.IO server: {e}")
            self._initialized = True
            return False

    async def _initialize_rabbitmq(self) -> bool:
        """Initialize RabbitMQ connection and exchanges."""
        # Connect to RabbitMQ
        connected = await self.rabbitmq.connect()
        if not connected:
            raise Exception("Failed to connect to RabbitMQ")

        # Declare exchanges
        await self.rabbitmq.declare_exchange("chat", "topic")
        await self.rabbitmq.declare_exchange("presence", "topic")
        await self.rabbitmq.declare_exchange("notifications", "topic")
        await self.rabbitmq.declare_exchange("auth", "topic")

        logger.info("RabbitMQ connection and exchanges initialized")
        return True

    async def shutdown(self) -> None:
        """Shutdown the Socket.IO server and its dependencies."""
        logger.info("Socket.IO server shutting down")
        await self.presence_manager.shutdown()
        await self.rabbitmq.close()

    async def _on_connect(self, sid: str, environ: Dict[str, Any], auth: Any) -> None:
        """Handle new socket connection."""
        logger.info(f"New client connected: {sid}")

        # Extract user ID from authorization header if present
        auth_data = environ.get("HTTP_AUTHORIZATION", "")
        if auth_data:
            # In a real implementation, you would validate the token
            # and extract the user ID from it
            user_id = auth_data  # Simplified for this example
            self.register_user(sid, user_id)
            logger.info(f"User {user_id} connected with sid {sid}")

    async def _on_disconnect(self, sid: str) -> None:
        """Handle socket disconnection."""
        logger.info(f"Client disconnected: {sid}")

        # Unregister user if associated with this sid
        user_id = self.unregister_user(sid)
        if user_id:
            logger.info(f"User {user_id} disconnected")
            # Publish presence update via RabbitMQ with retry
            try:
                await with_retry(
                    lambda: self._publish_presence_update(user_id, "offline"),
                    max_attempts=3,
                    circuit_breaker=self.rabbitmq_cb
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish presence update for {user_id}: {e}"
                )

    async def _publish_presence_update(
        self, user_id: str, status: str
    ) -> Never:
        """Publish presence update to RabbitMQ."""
        await self.rabbitmq.publish_message(
            exchange="user_events",
            routing_key=f"status.{user_id}",
            message=json.dumps({
                "type": "status_update",
                "user_id": user_id,
                "status": status,
                "last_changed": datetime.now().timestamp()
            })
        )
        # Ensures Never return type
        raise Exception("Presence update complete")

    async def _on_error(self, sid: str, error: Exception) -> None:
        """Handle socket error."""
        logger.error(f"Socket error for {sid}: {error}")

    async def _on_chat_message(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle chat message."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(
                f"Message received from unauthenticated socket: {sid}")
            return

        # Add user_id to message data
        message_data = {
            **data,
            "user_id": user_id,
            "timestamp": "now"
        }

        # 1. Send directly to room participants for immediate delivery
        room = data.get("room", "general")
        await self.emit_to_room(room, "chat_message", message_data)

        # 2. Publish to RabbitMQ for persistence and service notifications
        try:
            await with_retry(
                lambda: self.rabbitmq.publish_message(
                    exchange="chat",
                    routing_key=room,
                    message=json.dumps(message_data)
                ),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb
            )
            # 3. Acknowledge message receipt to sender
            await self.sio.emit(
                "message_received",
                message_data,
                room=sid
            )
        except Exception as e:
            logger.error(f"Failed to publish chat message: {e}")
            # Notify sender of the error
            await self.sio.emit(
                "message_error",
                {"error": "Failed to deliver message"},
                room=sid
            )

    async def _on_presence_update(
        self, sid: str, data: Dict[str, Any]
    ) -> None:
        """Handle presence update."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(
                f"Presence update from unauthenticated socket: {sid}")
            return

        # Add user_id to presence data
        presence_data = {
            **data,
            "type": "status_update",
            "user_id": user_id,
            "last_changed": datetime.now().timestamp()
        }

        # Publish presence update to RabbitMQ with retry
        try:
            await with_retry(
                lambda: self.rabbitmq.publish_message(
                    exchange="user_events",
                    routing_key=f"status.{user_id}",
                    message=json.dumps(presence_data)
                ),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb
            )
        except Exception as e:
            logger.error(f"Failed to publish presence update: {e}")

    def register_user(self, sid: str, user_id: str) -> None:
        """Register a user with a socket ID."""
        self.sid_to_user[sid] = user_id
        self.user_to_sid[user_id] = sid

    def unregister_user(self, sid: str) -> Optional[str]:
        """Unregister a user by socket ID."""
        user_id = self.sid_to_user.pop(sid, None)
        if user_id:
            self.user_to_sid.pop(user_id, None)
        return user_id

    def get_user_id_from_sid(self, sid: str) -> Optional[str]:
        """Get user ID from socket ID."""
        return self.sid_to_user.get(sid)

    def get_sid_from_user_id(self, user_id: str) -> Optional[str]:
        """Get socket ID from user ID."""
        return self.user_to_sid.get(user_id)

    async def emit_to_user(
        self, user_id: str, event: str, data: Dict[str, Any]
    ) -> bool:
        """Emit an event to a specific user."""
        sid = self.get_sid_from_user_id(user_id)
        if sid:
            await self.sio.emit(event, data, room=sid)
            return True
        return False

    async def broadcast(self, event: str, data: Dict[str, Any]) -> None:
        """Broadcast an event to all connected clients."""
        await self.sio.emit(event, data)

    async def join_room(self, sid: str, room: str) -> None:
        """Join a room."""
        await self.sio.enter_room(sid, room)
        logger.info(f"Client {sid} joined room {room}")

    async def leave_room(self, sid: str, room: str) -> None:
        """Leave a room."""
        await self.sio.leave_room(sid, room)
        logger.info(f"Client {sid} left room {room}")

    async def emit_to_room(
        self, room: str, event: str, data: Dict[str, Any]
    ) -> None:
        """Emit an event to all clients in a room."""
        await self.sio.emit(event, data, room=room)
