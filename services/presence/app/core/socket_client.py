import logging
from typing import Dict, Any, Optional
import socketio
import aiohttp

logger = logging.getLogger(__name__)


class SocketClient:
    """Client for interacting with the Socket.IO service."""

    def __init__(self, url: str):
        """Initialize the Socket.IO client.

        Args:
            url: URL of the Socket.IO service
        """
        self.url = url
        self.sio = socketio.AsyncClient()
        self.http_client = aiohttp.ClientSession()
        self.sid_to_user: Dict[str, str] = {}  # sid -> user_id mapping
        self._connected = False

    async def initialize(self) -> None:
        """Connect to the Socket.IO service."""
        try:
            await self.sio.connect(self.url)
            self._connected = True
            logger.info(f"Connected to Socket.IO service at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Socket.IO service: {e}")
            raise

    async def shutdown(self) -> None:
        """Disconnect from the Socket.IO service."""
        try:
            if self._connected:
                await self.sio.disconnect()
                self._connected = False
            await self.http_client.close()
            logger.info("Disconnected from Socket.IO service")
        except Exception as e:
            logger.error(f"Error disconnecting from Socket.IO service: {e}")

    def register_user(self, sid: str, user_id: str) -> None:
        """Register a user with their socket ID."""
        self.sid_to_user[sid] = user_id
        logger.debug(f"Registered user {user_id} with socket {sid}")

    def unregister_user(self, sid: str) -> Optional[str]:
        """Unregister a user by their socket ID."""
        user_id = self.sid_to_user.pop(sid, None)
        if user_id:
            logger.debug(f"Unregistered user {user_id} with socket {sid}")
        return user_id

    def get_user_id_from_sid(self, sid: str) -> Optional[str]:
        """Get user ID from socket ID."""
        return self.sid_to_user.get(sid)

    def get_sid_from_user_id(self, user_id: str) -> Optional[str]:
        """Get socket ID from user ID."""
        for sid, uid in self.sid_to_user.items():
            if uid == user_id:
                return sid
        return None

    async def emit_to_client(self, sid: str, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to a specific client."""
        try:
            # If we're directly connected to socket.io, use the client
            if self._connected:
                await self.sio.emit(event, data, room=sid)
            # Otherwise use the HTTP API
            else:
                async with self.http_client.post(
                    f"{self.url}/api/emit_to_client",
                    json={"sid": sid, "event": event, "data": data}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error emitting to client: {await response.text()}")
                        raise Exception(
                            f"Error emitting to client: {response.status}")
            logger.debug(f"Emitted {event} to client {sid}")
        except Exception as e:
            logger.error(f"Error emitting {event} to client {sid}: {e}")

    async def emit_to_user(self, user_id: str, event: str, data: Dict[str, Any]) -> bool:
        """Emit an event to a specific user by their user ID."""
        sid = self.get_sid_from_user_id(user_id)
        if sid:
            await self.emit_to_client(sid, event, data)
            return True
        return False

    async def broadcast(self, event: str, data: Dict[str, Any], skip_sid: Optional[str] = None) -> None:
        """Broadcast an event to all connected clients."""
        try:
            if self._connected:
                await self.sio.emit(event, data, skip_sid=skip_sid)
            else:
                payload = {"event": event, "data": data}
                if skip_sid:
                    payload["skip_sid"] = skip_sid
                async with self.http_client.post(
                    f"{self.url}/api/broadcast",
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error broadcasting: {await response.text()}")
                        raise Exception(
                            f"Error broadcasting: {response.status}")
            logger.debug(f"Broadcasted {event} to all clients")
        except Exception as e:
            logger.error(f"Error broadcasting {event}: {e}")
