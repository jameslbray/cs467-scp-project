from typing import Dict, Any, Optional, TypedDict, Union
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
    PRESENCE_UPDATE = "presence:update"
    PRESENCE_QUERY = "presence:query"

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
    recipient_id: str
    message_id: str
    content: str
    metadata: Optional[Dict[str, Any]]


class PresenceEvent(BaseEvent):
    """Presence-related event structure."""
    user_id: str
    status: UserStatus
    last_seen: float
    metadata: Optional[Dict[str, Any]]


class NotificationEvent(BaseEvent):
    """Notification event structure."""
    recipient_id: str
    title: str
    message: str
    level: str  # info, warning, error, success
    data: Optional[Dict[str, Any]]


class SystemEvent(BaseEvent):
    """System event structure."""
    level: str  # info, warning, error
    message: str
    details: Optional[Dict[str, Any]]


# Type for all possible event types
Event = Union[UserEvent, ChatEvent,
              PresenceEvent, NotificationEvent, SystemEvent]


def create_event(
    event_type: EventType,
    source: str,
    **kwargs
) -> Event:
    """Create a properly formatted event.

    Args:
        event_type: Type of event to create
        source: Service that is emitting the event
        **kwargs: Additional event-specific data

    Returns:
        A properly formatted event dictionary
    """
    import time

    base_event = {
        "type": event_type,
        "timestamp": time.time(),
        "source": source
    }

    return {**base_event, **kwargs}
