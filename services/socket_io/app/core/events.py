from typing import Dict, Any, Optional, TypedDict, Union
from enum import Enum
from datetime import datetime
from socketio import AsyncServer
from ..utils.utils import json_serial
import json
from services.rabbitmq.core.client import RabbitMQClient


class EventType(str, Enum):
    """Standard event types for service-to-service communication."""
    # Auth events
    AUTH_REGISTER = "auth:register"
    AUTH_LOGIN = "auth:login"
    AUTH_LOGOUT = "auth:logout"
    AUTH_VALIDATE = "auth:validate"

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


def create_event(event_type: EventType, source: str, **kwargs) -> Event:
    """Create a properly formatted event."""
    base_event = {
        "type": event_type,
        "timestamp": datetime.now().timestamp(),
        "source": source
    }
    return {**base_event, **kwargs}


class AuthEvents:
    """Handles authentication-related Socket.IO events."""

    def __init__(self, sio: AsyncServer, rabbitmq: RabbitMQClient):
        self.sio = sio
        self.rabbitmq = rabbitmq
        self.setup_handlers()

    def setup_handlers(self):
        @self.sio.on('auth:register')
        async def handle_register(sid: str, data: Dict[str, Any]):
            try:
                event = create_event(
                    EventType.AUTH_REGISTER,
                    "socket_io",
                    **data
                )

                # Publish registration request to RabbitMQ
                response = await self.rabbitmq.publish_and_wait(
                    exchange='auth',
                    routing_key='auth.register',
                    message=event,
                    correlation_id=sid
                )

                # Send response back to client
                if response.get('error'):
                    await self.sio.emit('auth:register:error', response, room=sid)
                else:
                    await self.sio.emit('auth:register:success', response, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    message=str(e)
                )
                await self.sio.emit('auth:register:error', error_event, room=sid)

        @self.sio.on('auth:login')
        async def handle_login(sid: str, data: Dict[str, Any]):
            try:
                event = create_event(
                    EventType.AUTH_LOGIN,
                    "socket_io",
                    **data
                )

                # Publish login request to RabbitMQ
                response = await self.rabbitmq.publish_and_wait(
                    exchange='auth',
                    routing_key='auth.login',
                    message=event,
                    correlation_id=sid
                )

                # Send response back to client
                if response.get('error'):
                    await self.sio.emit('auth:login:error', response, room=sid)
                else:
                    # Store the user's socket ID for future reference
                    await self.sio.save_session(sid, {'user_id': response['user']['id']})
                    await self.sio.emit('auth:login:success', response, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    message=str(e)
                )
                await self.sio.emit('auth:login:error', error_event, room=sid)

        @self.sio.on('auth:logout')
        async def handle_logout(sid: str):
            try:
                session = await self.sio.get_session(sid)
                user_id = session.get('user_id')

                if user_id:
                    event = create_event(
                        EventType.AUTH_LOGOUT,
                        "socket_io",
                        user_id=user_id
                    )

                    # Publish logout request to RabbitMQ
                    response = await self.rabbitmq.publish_and_wait(
                        exchange='auth',
                        routing_key='auth.logout',
                        message=event,
                        correlation_id=sid
                    )

                    # Clear session and send response
                    await self.sio.save_session(sid, {})
                    await self.sio.emit('auth:logout:success', response, room=sid)
                else:
                    error_event = create_event(
                        EventType.SYSTEM_ERROR,
                        "socket_io",
                        message="Not logged in"
                    )
                    await self.sio.emit('auth:logout:error', error_event, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    message=str(e)
                )
                await self.sio.emit('auth:logout:error', error_event, room=sid)
