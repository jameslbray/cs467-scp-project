from typing import Dict, Any, Optional, TypedDict, Union, Literal
from enum import Enum


class EventType(str, Enum):
    """Standard event types for service-to-service communication."""

    # User events
    USER_CONNECTED = "user:connected"
    USER_DISCONNECTED = "user:disconnected"
    USER_STATUS_CHANGED = "user:status_changed"

    # Chat events
    CHAT_MESSAGE = "chat:message"
    CHAT_TYPING = "chat:typing"
    CHAT_READ = "chat:read"

    # Presence events
    PRESENCE_STATUS_UPDATE = "presence:status:update"
    PRESENCE_STATUS_QUERY = "presence:status:query"
    PRESENCE_STATUS_CHANGED = "presence:status:changed"  # For notifications
    PRESENCE_FRIEND_STATUSES = "presence:friend:statuses"
    PRESENCE_FRIEND_STATUS_CHANGED = "presence:friend:status:changed"

    # Notification events
    NOTIFICATION = "notification"

    # System events
    SYSTEM_ERROR = "system:error"
    SYSTEM_INFO = "system:info"


class UserStatus(str, Enum):
    """User status types."""

    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


class BaseEvent(TypedDict):
    """Base event structure."""

    type: EventType
    timestamp: float
    source: str  # Service that emitted the event


class UserEvent(BaseEvent):
    """User-related event structure."""

    user_id: str
    data: Dict[str, Any]


class ChatEvent(BaseEvent):
    """Chat-related event structure."""

    sender_id: str
    room_id: str
    message_id: str
    content: str
    metadata: Optional[Dict[str, Any]]


class ChatTypingEvent(BaseEvent):
    """Chat typing event structure."""

    sender_id: str
    room_id: str
    is_typing: bool


class PresenceEvent(BaseEvent):
    """Presence-related event structure."""

    user_id: str
    status: UserStatus
    last_status_change: float
    metadata: Optional[Dict[str, Any]]


class NotificationEvent(BaseEvent):
    """Notification event structure."""

    recipient_id: str
    sender_id: str
    reference_id: str
    content_preview: str
    status: Literal["delivered", "undelivered", "error"]
    error: Optional[str] = None
    read: Optional[bool] = None
    notification_type: Literal["message", "friend_request", "status_update"]


class SystemEvent(BaseEvent):
    """System event structure."""

    level: str  # info, warning, error
    message: str
    details: Optional[Dict[str, Any]]


# Type for all possible event types
Event = Union[UserEvent, ChatEvent, PresenceEvent, NotificationEvent,
              SystemEvent]


def create_event(event_type: EventType, source: str, **kwargs) -> Event:
    """Create a properly formatted event.

    Args:
        event_type: Type of event to create
        source: Service that is emitting the event
        **kwargs: Additional event-specific data

    Returns:
        A properly formatted event dictionary
    """
    import time

    timestamp = float(time.time())

    if event_type in {
        EventType.USER_CONNECTED,
        EventType.USER_DISCONNECTED,
        EventType.USER_STATUS_CHANGED
    }:
        # UserEvent
        if "user_id" not in kwargs or "data" not in kwargs:
            raise ValueError("UserEvent requires 'user_id' and 'data'")
        return UserEvent(
            type=event_type,
            timestamp=timestamp,
            source=source,
            user_id=kwargs["user_id"],
            data=kwargs["data"]
        )
    elif event_type in {
        EventType.CHAT_MESSAGE,
        EventType.CHAT_TYPING,
        EventType.CHAT_READ
    }:
        # ChatEvent
        required = ["sender_id", "room_id", "message_id", "content"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"ChatEvent requires '{key}'")
        return ChatEvent(
            type=event_type,
            timestamp=timestamp,
            source=source,
            sender_id=kwargs["sender_id"],
            room_id=kwargs["room_id"],
            message_id=kwargs["message_id"],
            content=kwargs["content"],
            metadata=kwargs.get("metadata")
        )
    elif event_type in {EventType.PRESENCE_UPDATE, EventType.PRESENCE_QUERY}:
        # PresenceEvent
        required = ["user_id", "status", "last_status_change"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"PresenceEvent requires '{key}'")
        return PresenceEvent(
            type=event_type,
            timestamp=timestamp,
            source=source,
            user_id=kwargs["user_id"],
            status=kwargs["status"],
            last_status_change=kwargs["last_status_change"],
            metadata=kwargs.get("metadata")
        )
    elif event_type == EventType.NOTIFICATION:
        # NotificationEvent
        required = ["recipient_id", "sender_id", "reference_id",
            "content_preview", "status", "notification_type", "error",
            "read"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"NotificationEvent requires '{key}'")
        return NotificationEvent(
            type=event_type,
            timestamp=timestamp,
            source=source,
            recipient_id=kwargs["recipient_id"],
            sender_id=kwargs["sender_id"],
            reference_id=kwargs["reference_id"],
            content_preview=kwargs["content_preview"],
            status=kwargs["status"],
            error=kwargs.get("error"),
            read=kwargs.get("read"),
            notification_type=kwargs["notification_type"],
            data=kwargs.get("data")
        )
    elif event_type in {EventType.SYSTEM_ERROR, EventType.SYSTEM_INFO}:
        # SystemEvent
        required = ["level", "message"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"SystemEvent requires '{key}'")
        return SystemEvent(
            type=event_type,
            timestamp=timestamp,
            source=source,
            level=kwargs["level"],
            message=kwargs["message"],
            details=kwargs.get("details")
        )
    else:
        raise ValueError(f"Unknown event type: {event_type}")
