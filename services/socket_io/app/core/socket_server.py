import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import socketio

from services.rabbitmq.core.client import RabbitMQClient
from services.rabbitmq.core.config import Settings as RabbitMQSettings
from services.shared.utils.retry import CircuitBreaker, with_retry

from .config import get_socket_io_config
from .events import AuthEvents, EventType, create_event

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
        self.sid_to_username: Dict[str, str] = {}  # sid -> username mapping
        self._initialized = False

        # Initialize RabbitMQ client with provided settings
        self.rabbitmq = RabbitMQClient(rabbitmq_settings)

        # Initialize circuit breakers
        self.rabbitmq_cb = CircuitBreaker(
            "rabbitmq", failure_threshold=3, reset_timeout=30
        )

        # Register event handlers
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("error", self._on_error)
        self.sio.on("chat_message", self._on_chat_message)

        self.sio.on("presence:status:update", self._on_presence_status_update)
        self.sio.on("presence:status:query", self._on_presence_status_query)
        self.sio.on("presence:friend:statuses", self._on_get_friend_statuses)

        self.sio.on("notifications:fetch", self._on_notifications_fetch)

        self.sio.on(
            "connections:get_friends", self.handle_get_friends
        )

        # Connections to General room, not specific to a user
        self.sio.on("get_connections", self._on_get_connections)

        # TODO: implement chat typing and chat read receipts functionality
        self.sio.on("chat_typing", self._on_chat_typing)
        self.sio.on("chat_read", self._on_chat_read)

        # Register auth event handlers
        self.auth_events = AuthEvents(self.sio, self.rabbitmq)
        # self.presence_events = PresenceEvents(self.sio, self.rabbitmq)

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
                circuit_breaker=self.rabbitmq_cb,
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
        await self.rabbitmq.declare_exchange("presence", "direct")
        await self.rabbitmq.declare_exchange("notifications", "topic")
        await self.rabbitmq.declare_exchange("auth", "topic")
        await self.rabbitmq.declare_exchange("connections", "topic")

        # Declare queues
        await self.rabbitmq.declare_queue("presence", durable=True)
        await self.rabbitmq.declare_queue("socket_notifications", durable=True)

        # Bind queue to presence exchange for status updates
        await self.rabbitmq.declare_queue("socket_notifications", durable=True)

        await self.rabbitmq.bind_queue(
            "presence", "presence", "status.updates"
        )

        await self.rabbitmq.bind_queue("presence", "presence", "status.query")

        await self.rabbitmq.bind_queue(
            "presence", "presence", "friend.statuses"
        )
        
        # Bind to all notification sources
        await self.rabbitmq.bind_queue(
            "socket_notifications",
            "notifications",
            "user.#"  # All user notifications
        )
        await self.rabbitmq.bind_queue(
            "socket_notifications",
            "connections", 
            "user.#"  # All connection events
        )
        await self.rabbitmq.bind_queue(
            "socket_notifications",
            "chat",
            "room.#"  # All chat room events
        )

        # Start consuming notification events
        await self.rabbitmq.consume(
            "socket_notifications", self._handle_notifications
        )

        # Start consuming connection events
        await self.rabbitmq.consume(
            "connections", self._handle_connections
        )

        # Start consuming presence updates
        await self.rabbitmq.consume("presence", self._handle_presence_update)
        
        logger.info("RabbitMQ connection and exchanges initialized")
        return True

    async def shutdown(self) -> None:
        """Shutdown the Socket.IO server and its dependencies."""
        logger.info("Socket.IO server shutting down")
        await self.rabbitmq.close()

    async def _on_connect(
        self, sid: str, environ: Dict[str, Any], auth: Any
    ) -> None:
        """Handle new socket connection."""
        logger.info(f"New client connected: {sid}")

        # Extract token from auth payload
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get("token")
        if not token:
            logger.warning("No token provided on connect, disconnecting.")
            await self.sio.disconnect(sid)
            return

        # Validate token via users service (RabbitMQ)
        try:
            response = await self.rabbitmq.publish_and_wait(
                exchange="auth",
                routing_key="auth.validate",
                message={"token": token},
                correlation_id=sid,
            )

            if response.get("error") or not response.get("user"):
                logger.warning(
                    f"Token validation failed: {response.get('message')}"
                )
                await self.sio.disconnect(sid)
                return

            user_id = response["user"]["id"]
            username = response["user"].get("username", "Unknown User")
            self.sid_to_username[sid] = username
            self.register_user(sid, user_id)
            logger.info(f"User {user_id} connected with sid {sid}")

            # Optionally, publish presence update via RabbitMQ
            try:
                await with_retry(
                    lambda: self._publish_presence_update(user_id, "online"),
                    max_attempts=3,
                    circuit_breaker=self.rabbitmq_cb,
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish presence update for {user_id}: {e}"
                )

            # Join the user to the "general" room by default
            await self.join_room(sid, "general")
            await self.sio.emit("refresh_connections", {}, room="general")

        except Exception as e:
            logger.error(f"Error during token validation: {e}")
            await self.sio.disconnect(sid)

    async def _on_error(self, sid: str, error: Exception) -> None:
        """Handle socket error."""
        logger.error(f"Socket error for {sid}: {error}")

    async def _on_chat_message(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle chat message."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(
                f"Message received from unauthenticated socket: {sid}"
            )
            return

        # Create chat message
        chat_message = {
            "id": data.get("id", ""),
            "sender_id": user_id,
            "room_id": data.get("room_id", ""),
            "content": data.get("content", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_edited": False,
        }

        room = data.get("room", "general")
        await self.emit_to_room(
            room, EventType.CHAT_MESSAGE.value, dict(chat_message)
        )

        try:
            await with_retry(
                lambda: self.rabbitmq.publish_message(
                    exchange="chat",
                    routing_key=room,
                    message=json.dumps(chat_message),
                ),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb,
            )

            await self.sio.emit("message_received", chat_message, room=sid)
            logger.info(f"Chat message published to {room}")
        except Exception as e:
            logger.error(f"Failed to publish chat message: {e}")
            # Notify sender of the error
            await self.sio.emit(
                "message_error",
                {"error": "Failed to deliver message"},
                room=sid,
            )

    async def _on_presence_status_update(
        self, sid: str, data: Dict[str, Any]
    ) -> None:
        """Handle presence status update."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(f"Presence update from unauthenticated socket: {sid}")
            await self.sio.emit(
                "presence:status:update:error",
                {"error": "Not authenticated"},
                room=sid,
            )
            return

        # Create structured presence event
        presence_event = create_event(
            event_type=EventType.PRESENCE_STATUS_UPDATE,
            source="socket_io",
            user_id=user_id,
            status=data.get("status", "offline"),
            last_status_change=datetime.now().timestamp(),
            metadata=data.get("metadata", {}),
        )

        # Publish presence update to RabbitMQ with retry
        try:
            await with_retry(
                lambda: self.rabbitmq.publish_message(
                    exchange="presence",
                    routing_key="status.updates",
                    message=json.dumps(presence_event),
                ),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb,
            )

            await self.sio.emit(
                "presence:status:update:success",
                {"status": data.get("status", "offline")},
                room=sid,
            )

        except Exception as e:
            logger.error(f"Failed to publish presence update: {e}")
            await self.sio.emit(
                "presence:status:update:error",
                {"error": "Failed to update status"},
                room=sid,
            )

    async def _on_presence_status_query(
        self, sid: str, data: Dict[str, Any]
    ) -> None:
        """Handle presence status query."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(f"Presence query from unauthenticated socket: {sid}")
            return

        try:
            # Query presence service via RabbitMQ
            response = await self.rabbitmq.publish_and_wait(
                exchange="presence",
                routing_key="status.query",
                message={
                    "type": EventType.PRESENCE_STATUS_QUERY.value,
                    "user_id": data.get("target_user_id", user_id),
                    "requester_id": user_id,
                },
                correlation_id=sid,
            )

            await self.sio.emit(
                "presence:status:query:success", response, room=sid
            )

        except Exception as e:
            logger.error(f"Failed to query presence status: {e}")
            await self.sio.emit(
                "presence:status:query:error",
                {"error": "Failed to query status"},
                room=sid,
            )

    async def _on_get_connections(self, sid: str) -> None:
        """ Handle request for active connections list."""
        connections = []
        for conn_sid, user_id in self.sid_to_user.items():
            rooms = list(self.sio.rooms(conn_sid))
            rooms = [
                r for r in rooms if r != conn_sid
            ]  # filter out private room (which is sid itself)
            username = self.sid_to_username.get(conn_sid)

            connections.append(
                {
                    "sid": conn_sid,
                    "user_id": user_id,
                    "username": username,
                    "room": rooms[0] if rooms else None,
                }
            )

        logger.info("Emitting connections_list:")
        for conn in connections:
            logger.info(conn)

        await self.sio.emit("connections_list", connections, room=sid)

    def register_user(
        self, sid: str, user_id: str, username: Optional[str] = None
    ) -> None:
        """Register a user with a socket ID."""
        self.sid_to_user[sid] = user_id
        self.user_to_sid[user_id] = sid
        if username:
            self.sid_to_username[sid] = username

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

    async def _on_disconnect(self, sid: str) -> None:
        """Handle socket disconnection."""
        logger.info(f"Client disconnected: {sid}")

        # Unregister user if associated with this sid
        user_id = self.unregister_user(sid)
        if user_id:
            logger.info(f"User {user_id} disconnected")
            # Optionally, publish presence update via RabbitMQ
            try:
                await with_retry(
                    lambda: self._publish_presence_update(user_id, "offline"),
                    max_attempts=3,
                    circuit_breaker=self.rabbitmq_cb,
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish presence update for {user_id}: {e}"
                )
        await self.sio.emit("refresh_connections", {})

    async def _publish_presence_update(
        self, user_id: str, status: str
    ) -> None:
        """Publish presence update to RabbitMQ."""
        try:
            # Create structured presence event
            presence_event = create_event(
                EventType.PRESENCE_STATUS_UPDATE,
                "socket_io",
                user_id=user_id,
                status=status,
                last_status_change=datetime.now().timestamp(),
                metadata={},
            )

            await self.rabbitmq.publish_message(
                exchange="presence",
                routing_key="status.updates",
                message=json.dumps(presence_event),
            )
            logger.debug(f"Published presence update for {user_id}: {status}")
        except Exception as e:
            logger.error(f"Failed to publish presence update: {e}")
            raise

    async def _on_chat_typing(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle chat typing."""
        pass

    async def _on_chat_read(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle chat read."""
        pass

    async def _handle_presence_update(self, message):
        """Handle presence updates from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())

            if body.get("source") == "socket_io":
                logger.debug("Ignoring socket.io update from presence source")
                await message.ack()
                return

            user_id = body.get("user_id")
            status = body.get("status")
            last_status_change = body.get("last_status_change")

            if not user_id or not status:
                logger.warning("Incomplete presence update received")
                await message.ack()
                return

            # Format the presence update for Socket.IO
            presence_data = {
                "user_id": user_id,
                "status": status,
                "last_status_change": last_status_change,
            }

            await self.sio.emit(
                EventType.PRESENCE_FRIEND_STATUS_CHANGED, presence_data
            )

            await message.ack()
        except Exception as e:
            logger.error(f"Error handling presence update from RabbitMQ: {e}")
            await message.nack(requeue=False)

    async def _notify_friends_of_status(self, user_id: str, status_data: dict):
        """Notify all online friends of a user's status change."""
        try:
            # Get friend list through RabbitMQ
            response = await self.rabbitmq.publish_and_wait(
                exchange="presence",
                routing_key="presence.get_friends",
                message={"user_id": user_id},
                timeout=5.0,
            )

            if not response or not response.get("friends"):
                return

            # For each online friend, send the status update
            for friend_id in response["friends"]:
                friend_sid = self.get_sid_from_user_id(friend_id)
                if friend_sid:  # If friend is connected
                    await self.sio.emit(
                        "friend_status_changed", status_data, room=friend_sid
                    )
        except Exception as e:
            logger.error(f"Failed to notify friends of status update: {e}")

    async def _on_get_friend_statuses(
        self, sid: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle request for friend statuses."""
        user_id = self.get_user_id_from_sid(sid)
        logger.info(
            f"Received friend status request from {sid}, user_id: {user_id}"
        )
        if not user_id:
            logger.error(
                f"Friend status request from unauthenticated socket: {sid}"
            )
            await self.sio.emit(
                "presence:friend:statuses:error",
                {"error": "Not authenticated"},
                room=sid,
            )
            return

        try:
            # Use publish_and_wait for RPC-style communication
            if data is None or "friend_ids" not in data or not data["friend_ids"]:
                logger.error(
                    f"Invalid data for friend statuses request: {data}"
                )
                await self.sio.emit(
                    "presence:friend:statuses:error",
                    {"error": "Invalid request data"},
                    room=sid,
                )
                return

            response = await self.rabbitmq.publish_and_wait(
                exchange="presence",
                routing_key="friends.statuses",
                message={
                    "user_id": user_id,
                    "friend_ids": data["friend_ids"],
                    "source": "socket_io",
                    "event_type": EventType.PRESENCE_FRIEND_STATUSES,
                },
                correlation_id=sid,
                timeout=10.0,
            )

            logger.info(f"Received friend statuses response: {response}")

            if response and "statuses" in response:
                await self.sio.emit(
                    "presence:friend:statuses:success",
                    {"statuses": response["statuses"]},
                    room=sid,
                )
            else:
                await self.sio.emit(
                    "presence:friend:statuses:error",
                    {"error": "No statuses received"},
                    room=sid,
                )

        except Exception as e:
            logger.error(f"Failed to get friend statuses: {e}")
            await self.sio.emit(
                "presence:friend:statuses:error", {"error": str(e)}, room=sid
            )

    async def _handle_friend_statuses_response(self, message):
        """Handle friend statuses response from presence service."""
        try:
            body = json.loads(message.body.decode())
            requesting_user_id = body.get("user_id")
            statuses = body.get("statuses", {})

            logger.info(
                f"Received friend statuses response for user {requesting_user_id}"
            )

            # Find the socket ID for the requesting user
            sid = self.get_sid_from_user_id(requesting_user_id)
            if sid:
                await self.sio.emit(
                    "presence:friend:statuses:success",
                    {"statuses": statuses},
                    room=sid,
                )
                logger.info(f"Sent friend statuses to socket {sid}")
            else:
                logger.warning(
                    f"No socket found for user {requesting_user_id}"
                )

            await message.ack()
        except Exception as e:
            logger.error(f"Error handling friend statuses response: {e}")
            await message.nack(requeue=False)

    async def _on_notifications_fetch(self, sid: str):
        """Handle request for all notifications."""
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            logger.error(
                f"Notifications fetch from unauthenticated socket: {sid}"
            )
            await self.sio.emit(
                "notifications:fetch:error",
                {"error": "Not authenticated"},
                room=sid,
            )
            return

        try:
            # Use publish_and_wait to get all notifications
            response = await self.rabbitmq.publish_and_wait(
                exchange="notifications",
                routing_key="user.get_all",
                message={"user_id": user_id},
                correlation_id=sid,
                timeout=5.0,
            )

            if response and "notifications" in response:
                await self.sio.emit(
                    "notifications:update", response["notifications"], room=sid
                )
            else:
                await self.sio.emit(
                    "notifications:fetch:error",
                    {"error": "Failed to fetch notifications"},
                    room=sid,
                )
        except Exception as e:
            logger.error(f"Failed to fetch notifications: {e}")
            await self.sio.emit(
                "notifications:fetch:error", {"error": str(e)}, room=sid
            )

    async def handle_get_friends(self, sid: str, data: Optional[Dict[str, Any]] = None):
        """Handle request for friends list."""
        user_id = self.get_user_id_from_sid(sid)
        logger.info(
            f"Received get friends request from {sid}, user_id: {user_id}"
        )
        if not user_id:
            logger.error(f"Get friends request from unauthenticated socket: {sid}")
            await self.sio.emit(
                "connections:get_friends:error",
                {"error": "Not authenticated"},
                room=sid,
            )
            return

        try:
            # Use publish_and_wait to get friends list
            response = await self.rabbitmq.publish_and_wait(
                exchange="connections",
                routing_key="user.get_friends",
                message={
                    "user_id": user_id,
                    "source": "socket_io",
                    "event_type": EventType.CONNECTION_GET_FRIENDS,
                    },
                correlation_id=sid,
                timeout=5.0,
            )
            logger.info(f"Received friends list response: {response}")

            if response and "friends" in response:
                await self.sio.emit(
                    "connections:get_friends:success", response['friends'], room=sid
                )
            else:
                await self.sio.emit(
                    "connections:get_friends:error",
                    {"error": "Failed to fetch friends"},
                    room=sid,
                )
        except Exception as e:
            logger.error(f"Failed to get friends list: {e}")
            await self.sio.emit(
                "connections:get_friends:error", {"error": str(e)}, room=sid
            )

    async def _handle_connections(self, message):
        """Handle connection-related messages from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type")
            user_id = body.get("user_id")
            sid = self.get_sid_from_user_id(user_id)

            if not sid:
                logger.warning(f"No socket found for user {user_id}")
                await message.ack()
                return

            if event_type == EventType.CONNECTION_GET_FRIENDS.value:
                # Handle get friends request
                friends = body.get("friends", [])
                await self.sio.emit(
                    "connections:get_friends:success",
                    {"friends": friends},
                    room=sid,
                )
            else:
                logger.warning(f"Unknown connection event type: {event_type}")

            await message.ack()
        except Exception as e:
            logger.error(f"Error handling connection message: {e}")
            await message.nack(requeue=False)
    
    async def _handle_notifications(self, message):
        """Central hub for handling all notification types from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            logger.info(f"Received notification: {body}")
            
            # Extract common fields
            source = body.get("source", "unknown")
            event_type = body.get("event_type", "unknown")
            
            # Route to appropriate specialized handler based on source/type
            if source == "chat" or event_type.startswith("room_"):
                # Handle chat notifications (rooms, messages)
                await self._handle_chat_notification(message, body)
            
            elif source == "connections" or event_type.startswith("friend_"):
                # Handle connection notifications (friend requests, etc.)
                await self._handle_connection_notification(message, body)
                
            # elif source == "presence" or event_type.startswith("presence:"):
            #     # Handle presence notifications (online status)
            #     await self._handle_presence_notification(message, body)
                
            else:
                # Generic notification handling for everything else
                await self._handle_generic_notification(message, body)
                
            # Message already acked by specialized handlers
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in notification: {e}")
            await message.nack(requeue=False)
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            await message.nack(requeue=False)
            
    async def _handle_generic_notification(self, message, body):
        """Handle standard notifications to specific users."""
        try:
            recipient_id = body.get("recipient_id")
            
            if not recipient_id:
                logger.warning(f"Notification missing recipient_id: {body}")
                await message.ack()
                return
                
            # Find recipient's socket connection
            sid = self.get_sid_from_user_id(recipient_id)
            if sid:
                # Emit notification to recipient's socket
                await self.sio.emit("notification:new", body, room=sid)
                logger.info(f"Emitted notification to user {recipient_id}")
            else:
                logger.info(f"User {recipient_id} not connected, notification not delivered")
                
            await message.ack()
        except Exception as e:
            logger.error(f"Error processing generic notification: {e}")
            await message.nack(requeue=False)

    async def _handle_connection_notification(self, message, body):
        """Handle connection-related notifications (friend requests, etc.)"""
        try:
            # Extract relevant fields
            event_type = body.get("event_type")
            recipient_id = body.get("recipient_id")
            
            if not recipient_id:
                logger.warning(f"Connection notification missing recipient_id: {body}")
                await message.ack()
                return
                
            # Find recipient's socket
            sid = self.get_sid_from_user_id(recipient_id)
            if not sid:
                logger.info(f"User {recipient_id} not connected, connection notification not delivered")
                await message.ack()
                return
                
            # Emit appropriate event based on connection type
            if event_type == "friend_request":
                await self.sio.emit("connection:friend_request", body, room=sid)
                logger.info(f"Emitted friend request notification to {recipient_id}")
            elif event_type == "friend_accepted":
                await self.sio.emit("connection:friend_accepted", body, room=sid)
                logger.info(f"Emitted friend acceptance notification to {recipient_id}")
            else:
                await self.sio.emit("connection:update", body, room=sid)
                
            await message.ack()
        except Exception as e:
            logger.error(f"Error processing connection notification: {e}")
            await message.nack(requeue=False)

    async def _handle_chat_notification(self, message, body):
        """Handle chat-related notifications (messages, room creation)"""
        try:
            event_type = body.get("event_type")
            
            # Route based on specific chat event type
            if event_type == "room_created":
                # Handle room created event 
                await self._handle_room_created_notification(body)
            # elif event_type == "new_message":
            #     # Handle new message notification
            #     await self._handle_message_notification(body) 
            else:
                # Default case for other chat events
                recipient_id = body.get("recipient_id")
                if recipient_id:
                    sid = self.get_sid_from_user_id(recipient_id)
                    if sid:
                        await self.sio.emit("chat:notification", body, room=sid)
                        
            await message.ack()
        except Exception as e:
            logger.error(f"Error processing chat notification: {e}")
            await message.nack(requeue=False)

    async def _handle_room_created_notification(self, message):
        """Handle chat notifications from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type")
            user_id = body.get("user_id")
            sid = self.get_sid_from_user_id(user_id)

            if not sid:
                logger.warning(f"No socket found for user {user_id}")
                await message.ack()
                return
            
            if event_type == EventType.CHAT_ROOM_CREATED.value:
                # Handle room created notification
                room_id = body.get("room_id")
                room_name = body.get("room_name")
                room_created_by = body.get("room_created_by")
                room_participant_ids = body.get("room_participant_ids")

                for participant_id in room_participant_ids:
                    if participant_id != room_created_by:
                        await self.sio.emit(
                            "chat:room_created",
                            {
                                "notification_id": body.get("notification_id"),
                                "recipient_id": participant_id,
                                "sender_id": room_created_by,
                                "reference_id": room_id,
                                "room_name": room_name,
                                "content_preview": "You've been added to a new room",
                                "timestamp": datetime.now().isoformat(),
                            },
                            room=self.get_sid_from_user_id(participant_id),
                        )
            # elif event_type == EventType.CHAT_MESSAGE_RECEIVED.value:
            #     # Handle message received notification
            #     message_id = body.get("message_id")
            #     message_content = body.get("message_content")
            #     message_sender = body.get("message_sender")
            #     message_timestamp = body.get("message_timestamp")
                
            #     await self.sio.emit(
            #         "chat:message_received",
            #         {
            #             "message_id": message_id,
            #             "message_content": message_content,
            #         },
            #     )
                
            else:
                logger.warning(f"Unknown chat event type: {event_type}")
                
            await message.ack()
        except Exception as e:
            logger.error(f"Error handling chat notification: {e}")
            await message.nack(requeue=False)