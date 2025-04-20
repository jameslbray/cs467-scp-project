# import json
import socketio
import logging

# from .models import UserStatus, StatusType
from .events import ServerEvents  # , ClientEvents


class SocketManager:
    """Manages WebSocket connections for the presence service"""

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize with a Socket.IO server instance"""
        self.logger = logging.getLogger(__name__)
        self.sio = sio
        self.connected_users: dict[str, set[str]] = {
        }  # user_id -> set of socket IDs

        # Register Socket.IO event handlers
        self.sio.on("connect", self.handle_connect)
        self.sio.on("disconnect", self.handle_disconnect)

    def register_handlers(self, event_handlers: dict[str, callable]):
        """Register handlers for socket events"""
        for event, handler in event_handlers.items():
            self.sio.on(event, handler)

    async def handle_connect(self, sid: str, environ: dict):
        """Handle new socket connection"""
        self.logger.info(f"New connection: {sid}")

    async def handle_disconnect(self, sid: str):
        """Handle socket disconnection"""
        self.logger.info(f"Disconnection: {sid}")

        # Find and remove user associated with this socket
        for user_id, sockets in self.connected_users.items():
            if sid in sockets:
                sockets.remove(sid)

                # If this was the last socket for the user, they're offline
                if len(sockets) == 0:
                    del self.connected_users[user_id]
                    return user_id

        return None

    def register_user_connection(self, user_id: str, sid: str) -> bool:
        """Register a socket connection for a user"""
        if user_id not in self.connected_users:
            self.connected_users[user_id] = set()

        self.connected_users[user_id].add(sid)
        return len(
            self.connected_users[user_id]
            ) == 1  # True if this is first connection

    async def emit_to_user(self, user_id: str, event: ServerEvents,
                           data: dict) -> None:
        """Emit an event to all sockets of a specific user"""
        if user_id in self.connected_users:
            for sid in self.connected_users[user_id]:
                await self.sio.emit(event.value, data, room=sid)

    async def emit_to_users(self, user_ids: list[str], event: ServerEvents,
                            data: dict) -> None:
        """Emit an event to multiple users"""
        for user_id in user_ids:
            await self.emit_to_user(user_id, event, data)

    def get_connected_users(self) -> list[str]:
        """Get list of currently connected users"""
        return list(self.connected_users.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected"""
        return user_id in self.connected_users and len(
            self.connected_users[user_id]) > 0

    def get_user_id_from_sid(self, sid: str) -> str | None:
        """Find user ID associated with a socket ID"""
        for user_id, sockets in self.connected_users.items():
            if sid in sockets:
                return user_id
        return None
