import logging
from typing import Any, Callable, Dict

import socketio

from services.socket_io.app.core.event_schema import Event, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Any]


class ServiceConnector:
    """Connector for Socket.IO communication between services."""

    def __init__(self, service_name: str, socket_url: str):
        """Initialize the service connector.

        Args:
            service_name: Name of the service using this connector
            socket_url: URL of the Socket.IO server
        """
        self.service_name = service_name
        self.socket_url = socket_url
        self.sio = socketio.AsyncClient()
        self.event_handlers: Dict[str, EventHandler] = {}

    async def initialize(self) -> None:
        """Initialize the connection to the Socket.IO server."""
        try:
            # Connect to the Socket.IO server
            await self.sio.connect(self.socket_url, wait_timeout=10)
            logger.info(
                f"{self.service_name} service connected to Socket.IO at {self.socket_url}")

            # Register a catch-all event handler
            @self.sio.event
            async def message(data: Dict[str, Any]):
                event_type = data.get("type")
                if event_type and event_type in self.event_handlers:
                    handler = self.event_handlers[event_type]
                    await handler(data)
                else:
                    logger.warning(
                        f"Received event with no handler: {event_type}")

            # Register service with the Socket.IO server
            # ! TODO: FIX 
            await self.sio.emit("register_service", {"service_name": self.service_name})

        except Exception as e:
            logger.error(f"Failed to connect to Socket.IO: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """Disconnect from the Socket.IO server."""
        if self.sio.connected:
            await self.sio.disconnect()
            logger.info(
                f"{self.service_name} service disconnected from Socket.IO")

    def on_event(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type: Type of event to handle
            handler: Function to call when event is received
        """
        self.event_handlers[event_type] = handler
        logger.debug(f"Registered handler for {event_type} events")

    async def emit_to_user(self, user_id: str, event_type: EventType, **data) -> None:
        """Emit an event to a specific user.

        Args:
            user_id: ID of the user to send the event to
            event_type: Type of event to emit
            **data: Event data
        """
        event_data = {
            "type": event_type,
            "target_user": user_id,
            **data
        }
        await self.sio.emit("message", event_data)

    async def join_room(self, room: str) -> None:
        """Join a room.

        Args:
            room: Name of the room to join
        """
        await self.sio.emit("join", {"room": room})
        logger.debug(f"Joined room: {room}")

    async def leave_room(self, room: str) -> None:
        """Leave a room.

        Args:
            room: Name of the room to leave
        """
        await self.sio.emit("leave", {"room": room})
        logger.debug(f"Left room: {room}")
