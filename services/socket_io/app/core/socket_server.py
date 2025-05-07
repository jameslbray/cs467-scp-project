import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Set, Any, Callable, Awaitable, Union

import socketio
from fastapi import Request

from services.rabbitmq.core.client import RabbitMQClient
from services.shared.utils.retry import with_retry
from services.presence.app.core.presence_manager import PresenceManager

logger = logging.getLogger(__name__)

class SocketServer:
    """
    A centralized Socket.IO server that manages connections, rooms, and message handling.
    This class fully encapsulates Socket.IO server creation and configuration.
    """

    def __init__(
        self,
        rabbitmq_client: Optional[RabbitMQClient] = None,
        presence_manager: Optional[PresenceManager] = None,
        cors_allowed_origins: Union[str, List[str]] = "*",
        ping_timeout: int = 20,
        ping_interval: int = 25,
        max_http_buffer_size: int = 5 * 1024 * 1024,
        debug_mode: bool = True,
        cors_credentials: bool = True
    ):
        """
        Initialize the Socket.IO server with dependencies and configuration.
        
        Args:
            rabbitmq_client: An existing RabbitMQ client
            presence_manager: An existing PresenceManager instance
            cors_allowed_origins: CORS allowed origins for Socket.IO
            ping_timeout: Socket.IO ping timeout in seconds
            ping_interval: Socket.IO ping interval in seconds
            max_http_buffer_size: Maximum HTTP buffer size in bytes
            debug_mode: Enable debug logging
        """
        # Core dependencies - can be provided or created on demand
        self.rabbitmq_client = rabbitmq_client
        self.presence_manager = presence_manager
        
        # Socket.IO configuration
        self.cors_allowed_origins = "http://localhost:5173"  # Hardcode for now
        self.ping_timeout = ping_timeout
        self.ping_interval = ping_interval
        self.max_http_buffer_size = max_http_buffer_size
        self.debug_mode = debug_mode
        
        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins=self.cors_allowed_origins,
            ping_timeout=self.ping_timeout,
            ping_interval=self.ping_interval,
            max_http_buffer_size=self.max_http_buffer_size,
            always_connect=True,
            cors_credentials=True,
            logger=self.debug_mode,
            engineio_logger=self.debug_mode
        )
        
        # Create Socket.IO ASGI app
        self.socket_asgi = socketio.ASGIApp(
            self.sio, 
            socketio_path='socket.io'
        )
        
        # State management
        self._initialized = False
        self._user_sid_map = {}  # Maps user_id to sid
        self._sid_user_map = {}  # Maps sid to user_id
        self._user_data = {}  # Stores additional user data
        self._rooms = {}  # Maps room_id to set of user_ids
        self._user_rooms = {}  # Maps user_id to set of room_ids

    def _setup_event_handlers(self):
        """Register event handlers with the Socket.IO server."""
        if not self.sio:
            logger.error("Cannot set up event handlers: No Socket.IO server available")
            return
            
        # Core Socket.IO events
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("error", self._on_error)
        self.sio.on("connect_error", self._on_connect_error)
        self.sio.on("ping", self._on_ping)
        
        # Custom application events
        self.sio.on("message", self._handle_message)
        self.sio.on("join_room", self._on_join_room)
        
        logger.info("Socket.IO event handlers registered")

    async def initialize(self):
        """
        Initialize the Socket.IO server and its dependencies if they weren't provided.
        This method is idempotent and can be called multiple times.
        """
        if self._initialized:
            logger.info("Socket.IO server already initialized")
            return

        logger.info("Initializing Socket.IO server")
        
        # Initialize RabbitMQ client if not provided
        if not self.rabbitmq_client:
            try:
                await self._initialize_rabbitmq()
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ: {e}")
                # Continue initialization - we'll retry connection later
        
        # Set up event handlers
        self._setup_event_handlers()
        
        # Initialize presence manager if available
        if self.presence_manager and not self.presence_manager._initialized:
            try:
                await self.presence_manager.initialize()
                logger.info("Presence manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize presence manager: {e}")
                # Continue initialization - we'll retry later
        
        self._initialized = True
        logger.info("Socket.IO server initialization complete")

    async def _initialize_rabbitmq(self):
        """Initialize RabbitMQ connection if not provided externally."""
        if self.rabbitmq_client:
            logger.info("Using provided RabbitMQ client")
            return
            
        # This would be implementation-specific based on your RabbitMQ setup
        # Create a new RabbitMQ client and connect
        import os

        from services.rabbitmq.core.config import Settings as RabbitMQSettings
        
        rabbitmq_settings = RabbitMQSettings(RABBITMQ_URL=os.getenv("RABBITMQ_URL"))
        self.rabbitmq_client = RabbitMQClient(rabbitmq_settings)
        
        await self.rabbitmq_client.connect()
        
        # Set up exchanges and queues as needed
        await self.rabbitmq_client.declare_exchange("messages", exchange_type="topic")
        await self.rabbitmq_client.declare_exchange("presence", exchange_type="fanout")
        
        logger.info("RabbitMQ initialized successfully")

    async def shutdown(self):
        """Gracefully shutdown the Socket.IO server and its dependencies."""
        logger.info("Shutting down Socket.IO server")
        
        # Close RabbitMQ connection if we created it
        if self.rabbitmq_client:
            try:
                await self.rabbitmq_client.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")
        
        # Reset state
        self._initialized = False
        logger.info("Socket.IO server shutdown complete")

    async def _on_connect(self, sid, environ):
        """
        Handle new socket connections.
        
        Args:
            sid: Socket.IO session ID
            environ: WSGI environment dictionary
        """
        logger.info(f"New connection: {sid}")
        
        try:
            # Extract authentication data from the request
            auth_token = None
            request = environ.get('asgi.scope', {})
            
            # Extract token from headers
            headers = request.get('headers', [])
            for name, value in headers:
                if name == b'authorization':
                    auth_header = value.decode('utf-8')
                    if auth_header.startswith('Bearer '):
                        auth_token = auth_header[7:]  # Remove 'Bearer ' prefix
                
            if not auth_token:
                # Check for token in query parameters
                query_string = environ.get('QUERY_STRING', '')
                query_params = dict(q.split('=') for q in query_string.split('&') if '=' in q)
                auth_token = query_params.get('token')
                
            if not auth_token:
                logger.warning(f"No authentication token for connection {sid}")
                await self.sio.disconnect(sid)
                return False
                
            # Validate the token - this would be implementation-specific
            # Here, you might call your auth service or validate JWT locally
            user_id, user_data = await self._validate_token(auth_token)
            
            if not user_id:
                logger.warning(f"Authentication failed for connection {sid}")
                await self.sio.disconnect(sid)
                return False
                
            # Register the user
            self.register_user(user_id, sid, user_data)
            
            # Emit welcome message
            await self.sio.emit('welcome', {'user_id': user_id}, room=sid)
            
            # Update presence if presence manager is available
            if self.presence_manager:
                await self._publish_presence_update(user_id, 'online')
                
            logger.info(f"User {user_id} connected with sid {sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error during connection: {e}")
            await self.sio.disconnect(sid)
            return False
    
    async def _validate_token(self, token):
        """
        Validate authentication token.
        Implementation would depend on your authentication system.
        
        Returns:
            tuple: (user_id, user_data) if valid, (None, None) if invalid
        """
        # This is a placeholder. In a real application, you would:
        # 1. Verify the token (JWT validation, check with auth service, etc.)
        # 2. Extract the user ID and any other relevant user data
        
        # Example with JWT:
        try:
            import jwt
            import os
            
            secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            
            user_id = payload.get("sub")
            user_data = {
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
            
            return user_id, user_data
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None, None

    async def _on_disconnect(self, sid):
        """
        Handle socket disconnections.
        
        Args:
            sid: Socket.IO session ID
        """
        try:
            # Get user ID from session ID
            user_id = self.get_user_id_from_sid(sid)
            if not user_id:
                logger.info(f"Unknown user disconnected: {sid}")
                return
                
            logger.info(f"User {user_id} disconnected (sid: {sid})")
            
            # Update presence if presence manager is available
            if self.presence_manager:
                await self._publish_presence_update(user_id, 'offline')
            
            # Clean up user's room memberships
            if user_id in self._user_rooms:
                for room_id in list(self._user_rooms[user_id]):
                    if room_id in self._rooms and user_id in self._rooms[room_id]:
                        self._rooms[room_id].remove(user_id)
                        
                        # If room is empty, remove it
                        if not self._rooms[room_id]:
                            del self._rooms[room_id]
            
            # Unregister the user
            self.unregister_user(user_id, sid)
            
        except Exception as e:
            logger.error(f"Error during disconnection of {sid}: {e}")

    async def _publish_presence_update(self, user_id, status):
        """
        Publish user presence update.
        
        Args:
            user_id: The user ID
            status: Presence status ('online', 'offline', etc.)
        """
        try:
            # Use the presence manager if available
            if self.presence_manager:
                await self.presence_manager.update_presence(user_id, status)
                return
                
            # Fall back to direct RabbitMQ publishing if no presence manager
            if self.rabbitmq_client:
                payload = {
                    "user_id": user_id,
                    "status": status,
                    "timestamp": str(int(asyncio.get_event_loop().time()))
                }
                
                await self.rabbitmq_client.publish(
                    exchange="presence",
                    routing_key="",  # For fanout exchange
                    message=payload
                )
                
            # Broadcast to connected clients
            await self.broadcast("presence_update", {
                "user_id": user_id,
                "status": status
            })
            
        except Exception as e:
            logger.error(f"Error publishing presence update for {user_id}: {e}")

    async def _on_error(self, sid, error_data):
        """
        Handle socket error events.
        
        Args:
            sid: Socket.IO session ID
            error_data: Error information
        """
        user_id = self.get_user_id_from_sid(sid)
        user_info = f"User {user_id}" if user_id else f"Unknown user (sid: {sid})"
        logger.error(f"Socket.IO error for {user_info}: {error_data}")

    async def _on_connect_error(self, sid, error_data):
        """Handle connection error events."""
        logger.error(f"Socket.IO connection error for sid {sid}: {error_data}")

    async def _on_ping(self, sid):
        """Handle ping events."""
        user_id = self.get_user_id_from_sid(sid)
        if user_id:
            logger.debug(f"Ping from user {user_id}")

    async def _handle_message(self, sid, data):
        """
        Handle incoming messages from clients.
        
        Args:
            sid: Socket.IO session ID
            data: Message data
        """
        try:
            # Get user ID from session
            user_id = self.get_user_id_from_sid(sid)
            if not user_id:
                logger.warning(f"Message from unknown user (sid: {sid})")
                return
                
            logger.info(f"Message from user {user_id}: {data}")
            
            # Validate message format
            if not isinstance(data, dict):
                await self.emit_to_user(user_id, "error", {
                    "message": "Invalid message format"
                })
                return
                
            # Extract message data
            message_type = data.get("type")
            room_id = data.get("room_id")
            content = data.get("content")
            recipient_id = data.get("recipient_id")
            
            if not message_type:
                await self.emit_to_user(user_id, "error", {
                    "message": "Message type is required"
                })
                return
                
            # Process based on message type
            if message_type == "chat":
                # Chat message requires room_id or recipient_id
                if not room_id and not recipient_id:
                    await self.emit_to_user(user_id, "error", {
                        "message": "Room ID or recipient ID is required for chat messages"
                    })
                    return
                    
                if not content:
                    await self.emit_to_user(user_id, "error", {
                        "message": "Message content is required"
                    })
                    return
                    
                # Create message object
                message = {
                    "id": str(uuid.uuid4()),
                    "type": message_type,
                    "sender_id": user_id,
                    "content": content,
                    "timestamp": str(int(asyncio.get_event_loop().time())),
                }
                
                # Add room_id or recipient_id based on what's provided
                if room_id:
                    message["room_id"] = room_id
                    
                    # Check if user is in the room
                    if (user_id not in self._user_rooms or 
                            room_id not in self._user_rooms[user_id]):
                        await self.emit_to_user(user_id, "error", {
                            "message": f"You are not a member of room {room_id}"
                        })
                        return
                        
                    # Send to room
                    await self.emit_to_room(room_id, "message", message)
                    
                    # Publish to message queue for persistence
                    if self.rabbitmq_client:
                        await self.rabbitmq_client.publish(
                            exchange="messages",
                            routing_key=f"room.{room_id}",
                            message=message
                        )
                    
                elif recipient_id:
                    message["recipient_id"] = recipient_id
                    
                    # Send to recipient
                    recipient_sid = self.get_sid_from_user_id(recipient_id)
                    if recipient_sid:
                        await self.emit_to_user(recipient_id, "message", message)
                    
                    # Also send a copy to the sender
                    await self.emit_to_user(user_id, "message", message)
                    
                    # Publish to message queue for persistence
                    if self.rabbitmq_client:
                        await self.rabbitmq_client.publish(
                            exchange="messages",
                            routing_key=f"direct.{user_id}.{recipient_id}",
                            message=message
                        )
            
            elif message_type == "typing":
                # Typing indicator
                if not room_id and not recipient_id:
                    return
                    
                typing_data = {
                    "user_id": user_id,
                    "typing": data.get("typing", True)
                }
                
                if room_id:
                    # Check if user is in the room
                    if (user_id not in self._user_rooms or 
                            room_id not in self._user_rooms[user_id]):
                        return
                        
                    typing_data["room_id"] = room_id
                    await self.emit_to_room(room_id, "typing", typing_data, skip_sender=True)
                    
                elif recipient_id:
                    typing_data["recipient_id"] = recipient_id
                    await self.emit_to_user(recipient_id, "typing", typing_data)
            
            else:
                # Unknown message type
                await self.emit_to_user(user_id, "error", {
                    "message": f"Unknown message type: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Error handling message from {sid}: {e}")
            await self.sio.emit("error", {"message": "Server error processing message"}, room=sid)

    async def _on_presence_update(self, data):
        """
        Handle presence updates from the presence manager or message queue.
        
        Args:
            data: Presence update data
        """
        try:
            user_id = data.get("user_id")
            status = data.get("status")
            
            if not user_id or not status:
                logger.warning(f"Invalid presence update: {data}")
                return
                
            logger.info(f"Presence update: User {user_id} is {status}")
            
            # Get user data
            user_data = self._user_data.get(user_id, {})
            username = user_data.get("username", user_id)
            
            # Create presence update message
            presence_message = {
                "user_id": user_id,
                "username": username,
                "status": status,
                "timestamp": data.get("timestamp") or str(int(asyncio.get_event_loop().time()))
            }
            
            # Find all rooms the user is in
            user_rooms = self._user_rooms.get(user_id, set())
            
            # Broadcast to all rooms the user is in
            for room_id in user_rooms:
                await self.emit_to_room(room_id, "presence_update", presence_message)
                
            # Also broadcast to all connected users
            await self.broadcast("presence_update", presence_message)
            
        except Exception as e:
            logger.error(f"Error handling presence update: {e}")

    def register_user(self, user_id, sid, user_data=None):
        """Register a user with their socket ID."""
        self._user_sid_map[user_id] = sid
        self._sid_user_map[sid] = user_id
        if user_data:
            self._user_data[user_id] = user_data

    def unregister_user(self, user_id, sid):
        """Unregister a user."""
        if user_id in self._user_sid_map:
            del self._user_sid_map[user_id]
        if sid in self._sid_user_map:
            del self._sid_user_map[sid]
        if user_id in self._user_data:
            del self._user_data[user_id]
        if user_id in self._user_rooms:
            del self._user_rooms[user_id]

    def get_user_id_from_sid(self, sid):
        """Get user ID from socket ID."""
        return self._sid_user_map.get(sid)

    def get_sid_from_user_id(self, user_id):
        """Get socket ID from user ID."""
        return self._user_sid_map.get(user_id)

    async def emit_to_user(self, user_id, event, data):
        """
        Emit an event to a specific user.
        
        Args:
            user_id: The user ID
            event: Event name
            data: Event data
        """
        sid = self.get_sid_from_user_id(user_id)
        if sid:
            await self.sio.emit(event, data, room=sid)
            return True
        return False

    async def broadcast(self, event, data):
        """Broadcast an event to all connected clients."""
        await self.sio.emit(event, data)

    async def join_room(self, user_id, room_id):
        """Add a user to a room."""
        sid = self.get_sid_from_user_id(user_id)
        if not sid:
            return False
            
        # Add to Socket.IO room
        await self.sio.enter_room(sid, room_id)
        
        # Track room membership
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(user_id)
        
        if user_id not in self._user_rooms:
            self._user_rooms[user_id] = set()
        self._user_rooms[user_id].add(room_id)
        
        return True

    async def leave_room(self, user_id, room_id):
        """Remove a user from a room."""
        sid = self.get_sid_from_user_id(user_id)
        if not sid:
            return False
            
        # Remove from Socket.IO room
        await self.sio.leave_room(sid, room_id)
        
        # Update room membership tracking
        if room_id in self._rooms and user_id in self._rooms[room_id]:
            self._rooms[room_id].remove(user_id)
            
            # If room is empty, remove it
            if not self._rooms[room_id]:
                del self._rooms[room_id]
        
        if user_id in self._user_rooms and room_id in self._user_rooms[user_id]:
            self._user_rooms[user_id].remove(room_id)
            
        return True

    async def emit_to_room(self, room_id, event, data, skip_sender=False):
        """
        Emit an event to all users in a room.
        
        Args:
            room_id: The room ID
            event: Event name
            data: Event data
            skip_sender: If True, don't send to the user who triggered the event
        """
        if skip_sender and isinstance(data, dict) and "user_id" in data:
            # Get the sender's SID to skip
            sender_id = data["user_id"]
            sender_sid = self.get_sid_from_user_id(sender_id)
            
            if sender_sid:
                await self.sio.emit(event, data, room=room_id, skip_sid=sender_sid)
                return
        
        # Default case: send to all in room
        await self.sio.emit(event, data, room=room_id)

    async def _on_join_room(self, sid, data):
        """
        Handle join room requests from clients.
        
        Args:
            sid: Socket.IO session ID
            data: Room data with room_id
        """
        user_id = self.get_user_id_from_sid(sid)
        if not user_id:
            return
            
        room_id = data.get("room_id")
        if not room_id:
            await self.sio.emit("error", {"message": "Room ID is required"}, room=sid)
            return
            
        success = await self.join_room(user_id, room_id)
        
        if success:
            # Notify user of successful join
            await self.sio.emit("room_joined", {"room_id": room_id}, room=sid)
            
            # Notify other room members
            if room_id in self._rooms:
                room_message = {
                    "room_id": room_id,
                    "user_id": user_id,
                    "action": "joined",
                    "timestamp": str(int(asyncio.get_event_loop().time()))
                }
                await self.emit_to_room(room_id, "room_update", room_message, skip_sender=True)

    def get_asgi_app(self):
        """Get the ASGI app for mounting in FastAPI."""
        return self.socket_asgi