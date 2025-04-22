"""
Socket.IO server implementation for the socket-io service.
Handles real-time messaging and integrates with the presence service.
"""

import logging
import socketio
from typing import Dict, Any, Optional

from app.core.config import get_socket_io_config, settings

# Configure logging
logger = logging.getLogger(__name__)


class SocketServer:
    """Socket.IO server implementation."""

    def __init__(self):
        """Initialize the Socket.IO server."""
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=settings.CORS_ORIGINS,
            logger=True,
            **get_socket_io_config()
        )
        self.app = socketio.ASGIApp(self.sio)
        self.sid_to_user: Dict[str, str] = {}  # sid -> user_id mapping
        self.user_to_sid: Dict[str, str] = {}  # user_id -> sid mapping
        self._initialized = False

        # Register event handlers
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('error', self._on_error)

    async def initialize(self) -> None:
        """Initialize the Socket.IO server."""
        if self._initialized:
            return

        logger.info("Socket.IO server initialized")
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the Socket.IO server."""
        logger.info("Socket.IO server shutting down")

    async def _on_connect(self, sid: str, environ: Dict[str, Any]) -> None:
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

    async def _on_error(self, sid: str, error: Exception) -> None:
        """Handle socket error."""
        logger.error(f"Socket error for {sid}: {error}")

    def register_user(self, sid: str, user_id: str) -> None:
        """Register a user with a socket ID."""
        self.sid_to_user[sid] = user_id
        self.user_to_sid[user_id] = sid

    def unregister_user(self, sid: str) -> Optional[str]:
        """Unregister a user with a socket ID."""
        user_id = self.sid_to_user.get(sid)
        if user_id:
            del self.sid_to_user[sid]
            if user_id in self.user_to_sid:
                del self.user_to_sid[user_id]
        return user_id

    def get_user_id_from_sid(self, sid: str) -> Optional[str]:
        """Get user ID from socket ID."""
        return self.sid_to_user.get(sid)

    def get_sid_from_user_id(self, user_id: str) -> Optional[str]:
        """Get socket ID from user ID."""
        return self.user_to_sid.get(user_id)

    async def emit_to_user(self, user_id: str, event: str, data: Dict[str, Any]) -> bool:
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
        self.sio.enter_room(sid, room)
        logger.info(f"Client {sid} joined room {room}")

    async def leave_room(self, sid: str, room: str) -> None:
        """Leave a room."""
        self.sio.leave_room(sid, room)
        logger.info(f"Client {sid} left room {room}")

    async def emit_to_room(self, room: str, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to all clients in a room."""
        await self.sio.emit(event, data, room=room)
