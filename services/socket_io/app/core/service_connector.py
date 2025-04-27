import logging
from typing import Dict, Callable, Awaitable, List, Optional
import socketio
import aiohttp

from .event_schema import Event, EventType, create_event

logger = logging.getLogger(__name__)


class ServiceConnector:
    """Connector for services to communicate via Socket.IO."""

    def __init__(self, service_name: str, socket_url: str):
        """Initialize the service connector.

        Args:
            service_name: Name of the service using this connector
            socket_url: URL of the Socket.IO service
        """
        self.service_name = service_name
        self.socket_url = socket_url
        self.sio = socketio.AsyncClient()
        self.http_client = aiohttp.ClientSession()
        self.sid_to_user: Dict[str, str] = {}  # sid -> user_id mapping
        self._connected = False
        self.event_handlers: Dict[
            EventType, List[Callable[[Event], Awaitable[None]]]
        ] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the connector and connect to the Socket.IO service."""
        if self._initialized:
            return

        # Register default event handlers
        self.sio.on("connect", self._on_connect)
        self.sio.on("disconnect", self._on_disconnect)
        self.sio.on("error", self._on_error)
        self.sio.on("event", self._handle_event)

        # Connect to the Socket.IO service
        try:
            await self.sio.connect(self.socket_url)
            self._connected = True
            self._initialized = True
            logger.info(f"Connected to Socket.IO service at {self.socket_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Socket.IO service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the connector and disconnect from the Socket.IO service."""
        if not self._initialized:
            return

        try:
            if self._connected:
                await self.sio.disconnect()
                self._connected = False
            await self.http_client.close()
            self._initialized = False
            logger.info("Disconnected from Socket.IO service")
        except Exception as e:
            logger.error(f"Error disconnecting from Socket.IO service: {e}")

    async def _on_connect(self) -> None:
        """Handle connection event."""
        logger.info(f"Connected to Socket.IO service as {self.service_name}")

    async def _on_disconnect(self) -> None:
        """Handle disconnection event."""
        logger.info("Disconnected from Socket.IO service")
        self._connected = False

    async def _on_error(self, error: Exception) -> None:
        """Handle error event."""
        logger.error(f"Socket.IO error: {error}")

    async def _handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        event_type = event.get("type")
        if not event_type:
            logger.warning("Received event without type")
            return

        try:
            event_type_enum = EventType(event_type)
            handlers = self.event_handlers.get(event_type_enum, [])
            for handler in handlers:
                await handler(event)
        except ValueError:
            logger.warning(f"Unknown event type: {event_type}")
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")

    def on_event(
        self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event {event_type}")

    def off_event(
        self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Unregister an event handler.

        Args:
            event_type: Type of event to unregister
            handler: Handler to unregister
        """
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                logger.debug(f"Unregistered handler for event {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event {event_type}")

    async def emit_event(self, event: Event) -> None:
        """Emit an event to the Socket.IO service.

        Args:
            event: Event to emit
        """
        try:
            if self._connected:
                await self.sio.emit("event", event)
                logger.debug(f"Emitted event {event.get('type')}")
            else:
                # Fallback to HTTP API if not connected
                async with self.http_client.post(
                    f"{self.socket_url}/api/emit", json=event
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error emitting event: {error_text}")
                        raise Exception(f"Error emitting event: {response.status}")
                logger.debug(f"Emitted event {event.get('type')} via HTTP API")
        except Exception as e:
            logger.error(f"Error emitting event {event.get('type')}: {e}")
            raise

    async def emit_to_user(self, user_id: str, event_type: EventType, **kwargs) -> bool:
        """Emit an event to a specific user.

        Args:
            user_id: ID of the user to emit to
            event_type: Type of event to emit
            **kwargs: Additional event data

        Returns:
            True if the event was emitted, False otherwise
        """
        sid = self.get_sid_from_user_id(user_id)
        if sid:
            await self.emit_to_client(sid, event_type, **kwargs)
            return True
        return False

    async def broadcast_event(self, event_type: EventType, **kwargs) -> None:
        """Broadcast an event to all connected clients.

        Args:
            event_type: Type of event to broadcast
            **kwargs: Additional event data
        """
        event = create_event(event_type, self.service_name, **kwargs)
        await self.emit_event(event)

    async def join_room(self, room: str) -> None:
        """Join a room.

        Args:
            room: Room to join
        """
        try:
            if self._connected:
                await self.sio.emit("join_room", {"room": room})
                logger.debug(f"Joined room {room}")
            else:
                # Fallback to HTTP API if not connected
                async with self.http_client.post(
                    f"{self.socket_url}/api/join_room", json={"room": room}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error joining room: {error_text}")
                        raise Exception(f"Error joining room: {response.status}")
                logger.debug(f"Joined room {room} via HTTP API")
        except Exception as e:
            logger.error(f"Error joining room {room}: {e}")
            raise

    async def leave_room(self, room: str) -> None:
        """Leave a room.

        Args:
            room: Room to leave
        """
        try:
            if self._connected:
                await self.sio.emit("leave_room", {"room": room})
                logger.debug(f"Left room {room}")
            else:
                # Fallback to HTTP API if not connected
                async with self.http_client.post(
                    f"{self.socket_url}/api/leave_room", json={"room": room}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error leaving room: {error_text}")
                        raise Exception(f"Error leaving room: {response.status}")
                logger.debug(f"Left room {room} via HTTP API")
        except Exception as e:
            logger.error(f"Error leaving room {room}: {e}")
            raise

    async def emit_to_room(self, room: str, event_type: EventType, **kwargs) -> None:
        """Emit an event to a specific room.

        Args:
            room: Room to emit to
            event_type: Type of event to emit
            **kwargs: Additional event data
        """
        event = create_event(event_type, self.service_name, **kwargs)
        try:
            if self._connected:
                await self.sio.emit("room_event", {"room": room, "event": event})
                logger.debug(f"Emitted event {event_type} to room {room}")
            else:
                # Fallback to HTTP API if not connected
                async with self.http_client.post(
                    f"{self.socket_url}/api/emit_to_room",
                    json={"room": room, "event": event},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error emitting to room: {error_text}")
                        raise Exception(f"Error emitting to room: {response.status}")
                logger.debug(f"Emitted event {event_type} to room {room} via HTTP API")
        except Exception as e:
            logger.error(f"Error emitting event {event_type} to room {room}: {e}")
            raise

    def register_user(self, sid: str, user_id: str) -> None:
        """Register a user with their socket ID.

        Args:
            sid: Socket ID
            user_id: User ID
        """
        self.sid_to_user[sid] = user_id
        logger.debug(f"Registered user {user_id} with socket {sid}")

    def unregister_user(self, sid: str) -> Optional[str]:
        """Unregister a user by their socket ID.

        Args:
            sid: Socket ID

        Returns:
            User ID if found, None otherwise
        """
        user_id = self.sid_to_user.pop(sid, None)
        if user_id:
            logger.debug(f"Unregistered user {user_id} with socket {sid}")
        return user_id

    def get_user_id_from_sid(self, sid: str) -> Optional[str]:
        """Get user ID from socket ID.

        Args:
            sid: Socket ID

        Returns:
            User ID if found, None otherwise
        """
        return self.sid_to_user.get(sid)

    def get_sid_from_user_id(self, user_id: str) -> Optional[str]:
        """Get socket ID from user ID.

        Args:
            user_id: User ID

        Returns:
            Socket ID if found, None otherwise
        """
        for sid, uid in self.sid_to_user.items():
            if uid == user_id:
                return sid
        return None

    async def emit_to_client(self, sid: str, event_type: EventType, **kwargs) -> None:
        """Emit an event to a specific client.

        Args:
            sid: Socket ID
            event_type: Type of event to emit
            **kwargs: Additional event data
        """
        event = create_event(event_type, self.service_name, **kwargs)
        try:
            if self._connected:
                await self.sio.emit("client_event", {"sid": sid, "event": event})
                logger.debug(f"Emitted event {event_type} to client {sid}")
            else:
                # Fallback to HTTP API if not connected
                async with self.http_client.post(
                    f"{self.socket_url}/api/emit_to_client",
                    json={"sid": sid, "event": event},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error emitting to client: {error_text}")
                        raise Exception(f"Error emitting to client: {response.status}")
                logger.debug(f"Emitted event {event_type} to client {sid} via HTTP API")
        except Exception as e:
            logger.error(f"Error emitting event {event_type} to client {sid}: {e}")
            raise
