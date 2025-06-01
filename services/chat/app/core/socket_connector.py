import logging
import os
from services.socket_io.app.core.event_schema import (
    EventType,
    UserEvent,
    ChatEvent,
    ChatTypingEvent,
)
from services.socket_io.app.core.service_connector import ServiceConnector

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SocketManager:
    """Socket.IO connector for the chat service."""

    def __init__(self):
        """Initialize the chat socket connector."""
        logger.info(f"SOCKET IO URL: {settings.SOCKET_IO_URL}")
        socket_url = os.environ.get("SOCKET_IO_URL", settings.SOCKET_IO_URL)
        self.connector = ServiceConnector("chat", socket_url)

    async def initialize(self) -> None:
        """Initialize the connector and register event handlers."""
        await self.connector.initialize()

        # Register event handlers
        self.connector.on_event(
            EventType.USER_CONNECTED, self._handle_user_connected
        )
        self.connector.on_event(
            EventType.USER_DISCONNECTED, self._handle_user_disconnected
        )
        self.connector.on_event(
            EventType.CHAT_MESSAGE, self._handle_chat_message
        )
        self.connector.on_event(
            EventType.CHAT_TYPING, self._handle_chat_typing
        )

    async def shutdown(self) -> None:
        """Shutdown the connector."""
        await self.connector.shutdown()

    async def _handle_user_connected(self, event: UserEvent) -> None:
        """Handle user connected event."""
        user_id = event["user_id"]
        logger.info(f"User {user_id} connected")

        # Join user's personal room
        await self.connector.join_room(f"user:{user_id}")

    async def _handle_user_disconnected(self, event: UserEvent) -> None:
        """Handle user disconnected event."""
        user_id = event["user_id"]
        logger.info(f"User {user_id} disconnected")

        # Leave user's personal room
        await self.connector.leave_room(f"user:{user_id}")

    async def _handle_chat_message(self, event: ChatEvent) -> None:
        """Handle chat message event."""
        sender_id = event["sender_id"]
        room_id = event["room_id"]
        message_id = event["message_id"]
        content = event["content"]

        logger.info(
            f"Chat message from {sender_id} to {room_id}: "
            f"{content[:50]}..."
        )

        # Emit message to recipient
        await self.connector.emit_to_user(
            room_id,
            EventType.CHAT_MESSAGE,
            sender_id=sender_id,
            room_id=room_id,
            message_id=message_id,
            content=content,
            room_name=event.get("name"),
        )

    async def _handle_chat_typing(self, event: ChatTypingEvent) -> None:
        """Handle chat typing event."""
        sender_id = event["sender_id"]
        room_id = event["room_id"]
        is_typing = event["is_typing"]

        logger.debug(
            f"User {sender_id} is {'typing' if is_typing else 'not typing'} "
            f"to {room_id}"
        )

        # Emit typing status to recipient
        await self.connector.emit_to_user(
            room_id,
            EventType.CHAT_TYPING,
            sender_id=sender_id,
            room_id=room_id,
            is_typing=is_typing,
        )

    async def send_message(
        self, sender_id: str, recipient_id: str, content: str
    ) -> str:
        """Send a chat message.

        Args:
            sender_id: ID of the sender
            recipient_id: ID of the recipient
            content: Message content

        Returns:
            ID of the sent message
        """
        import uuid

        message_id = str(uuid.uuid4())

        # Emit message to recipient
        await self.connector.emit_to_user(
            recipient_id,
            EventType.CHAT_MESSAGE,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_id=message_id,
            content=content,
            )

        return message_id

    async def send_typing_status(
        self, sender_id: str, recipient_id: str, is_typing: bool = True
    ) -> None:
        """Send typing status.

        Args:
            sender_id: ID of the sender
            recipient_id: ID of the recipient
            is_typing: Whether the sender is typing
        """
        await self.connector.emit_to_user(
            recipient_id,
            EventType.CHAT_TYPING,
            sender_id=sender_id,
            recipient_id=recipient_id,
            is_typing=is_typing,
        )
