from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, TypedDict, Union, Literal

from socketio import AsyncServer

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
    PRESENCE_STATUS_UPDATE = "presence:status:update"
    PRESENCE_STATUS_QUERY = "presence:status:query"
    PRESENCE_STATUS_CHANGED = "presence:status:changed"
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
    recipient_id: str
    message_id: str
    content: str
    metadata: Optional[Dict[str, Any]]


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


class PresenceEvents:
    """Handles presence-related Socket.IO events."""

    def __init__(self, sio: AsyncServer, rabbitmq: RabbitMQClient):
        self.sio = sio
        self.rabbitmq = rabbitmq
        self.setup_handlers()

    def setup_handlers(self):
        @self.sio.on('presence:status:update')
        async def handle_presence_status_update(sid: str, data: Dict[str, Any]):
            try:
                session = await self.sio.get_session(sid)
                user_id = session.get('user_id')

                if not user_id:
                    error_event = create_event(
                        EventType.SYSTEM_ERROR,
                        "socket_io",
                        level="error",
                        message="User not authenticated",
                        details={}
                    )
                    await self.sio.emit('presence:status:update:error', error_event, room=sid)
                    return

                event = create_event(
                    EventType.PRESENCE_STATUS_UPDATE,
                    "socket_io",
                    user_id=user_id,
                    status=data.get('status', UserStatus.ONLINE),
                    last_status_change=datetime.now().timestamp(),
                    metadata=data.get('metadata', {})
                )

                # Publish presence update to RabbitMQ
                response = await self.rabbitmq.publish_and_wait(
                    exchange='presence',
                    routing_key='status.updates',
                    message=event,
                    correlation_id=sid,
                    timeout=10.0
                )

                if response.get('error'):
                    await self.sio.emit('presence:status:update:error', response, room=sid)
                else:
                    await self.sio.emit('presence:status:update:success', {
                        "status": data.get('status', UserStatus.ONLINE),
                        "user_id": user_id,
                        "timestamp": datetime.now().timestamp()
                    }, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    level="error",
                    message=str(e),
                    details={}
                )
                await self.sio.emit('presence:status:update:error', error_event, room=sid)
        
        @self.sio.on('presence:status:query')
        async def handle_presence_status_query(sid: str, data: Dict[str, Any]):
            try:
                session = await self.sio.get_session(sid)
                user_id = session.get('user_id')

                if not user_id:
                    error_event = create_event(
                        EventType.SYSTEM_ERROR,
                        "socket_io",
                        level="error",
                        message="User not authenticated",
                        details={}
                    )
                    await self.sio.emit('presence:status:query:error', error_event, room=sid)
                    return

                event = create_event(
                    EventType.PRESENCE_STATUS_QUERY,
                    "socket_io",
                    user_id=user_id,
                    target_user_id=data.get('target_user_id', user_id),
                    status=UserStatus.ONLINE,
                    last_status_change=datetime.now().timestamp(),
                    metadata={}
                )

                # Publish presence query to RabbitMQ
                response = await self.rabbitmq.publish_and_wait(
                    exchange='presence',
                    routing_key='status.query',
                    message=event,
                    correlation_id=sid,
                    timeout=10.0
                )

                if response.get('error'):
                    await self.sio.emit('presence:status:query:error', response, room=sid)
                else:
                    await self.sio.emit('presence:status:query:success', response, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    level="error",
                    message=str(e),
                    details={}
                )
                await self.sio.emit('presence:status:query:error', error_event, room=sid)

        # Handle friend statuses request with standardized event name
        @self.sio.on('presence:friend:statuses')
        async def handle_presence_friend_statuses(sid: str, data: Dict[str, Any] = None):
            try:
                session = await self.sio.get_session(sid)
                user_id = session.get('user_id')

                if not user_id:
                    error_event = create_event(
                        EventType.SYSTEM_ERROR,
                        "socket_io",
                        level="error",
                        message="User not authenticated",
                        details={}
                    )
                    await self.sio.emit('presence:friend:statuses:error', error_event, room=sid)
                    return

                # Create a simple message for friend statuses request
                message = {
                    "type": "presence:friend:statuses",
                    "user_id": user_id,
                    "timestamp": datetime.now().timestamp()
                }

                # Publish friend statuses request to RabbitMQ
                response = await self.rabbitmq.publish_and_wait(
                    exchange='presence',
                    routing_key='friend.statuses',
                    message=message,
                    correlation_id=sid,
                    timeout=15.0  # Higher timeout for friend queries
                )

                # Send standardized response events
                if response.get('error'):
                    await self.sio.emit('presence:friend:statuses:error', response, room=sid)
                else:
                    await self.sio.emit('presence:friend:statuses:success', {
                        "statuses": response.get('statuses', {}),
                        "timestamp": datetime.now().timestamp()
                    }, room=sid)
            except Exception as e:
                error_event = create_event(
                    EventType.SYSTEM_ERROR,
                    "socket_io",
                    level="error",
                    message=str(e),
                    details={}
                )
                await self.sio.emit('presence:friend:statuses:error', error_event, room=sid)

        # # Handle chat message events with standardized names
        # @self.sio.on('chat:message')
        # async def handle_chat_message(sid: str, data: Dict[str, Any]):
        #     try:
        #         session = await self.sio.get_session(sid)
        #         user_id = session.get('user_id')

        #         if not user_id:
        #             error_event = create_event(
        #                 EventType.SYSTEM_ERROR,
        #                 "socket_io",
        #                 level="error",
        #                 message="User not authenticated",
        #                 details={}
        #             )
        #             await self.sio.emit('chat:message:error', error_event, room=sid)
        #             return

        #         event = create_event(
        #             EventType.CHAT_MESSAGE,
        #             "socket_io",
        #             sender_id=user_id,
        #             recipient_id=data.get('recipient_id', ''),
        #             message_id=data.get('message_id', ''),
        #             content=data.get('content', ''),
        #             metadata=data.get('metadata', {})
        #         )

        #         # Publish chat message to RabbitMQ
        #         response = await self.rabbitmq.publish_and_wait(
        #             exchange='chat',
        #             routing_key='messages',
        #             message=event,
        #             correlation_id=sid,
        #             timeout=10.0
        #         )

        #         # Send standardized response events
        #         if response.get('error'):
        #             await self.sio.emit('chat:message:error', response, room=sid)
        #         else:
        #             await self.sio.emit('chat:message:success', response, room=sid)
        #     except Exception as e:
        #         error_event = create_event(
        #             EventType.SYSTEM_ERROR,
        #             "socket_io",
        #             level="error",
        #             message=str(e),
        #             details={}
        #         )
        #         await self.sio.emit('chat:message:error', error_event, room=sid)

        # # NEW: Handle typing events with standardized names
        # @self.sio.on('chat:typing')
        # async def handle_chat_typing(sid: str, data: Dict[str, Any]):
        #     try:
        #         session = await self.sio.get_session(sid)
        #         user_id = session.get('user_id')

        #         if not user_id:
        #             return  # Don't send error for typing events

        #         # Broadcast typing status to room
        #         room = data.get('room', 'general')
        #         typing_data = {
        #             "user_id": user_id,
        #             "room": room,
        #             "is_typing": data.get('is_typing', False),
        #             "timestamp": datetime.now().timestamp()
        #         }
                
        #         await self.sio.emit('chat:typing:update', typing_data, room=room, skip_sid=sid)
        #     except Exception as e:
        #         # Don't send errors for typing events to avoid spam
        #         pass

        # # NEW: Handle read receipt events with standardized names
        # @self.sio.on('chat:read')
        # async def handle_chat_read(sid: str, data: Dict[str, Any]):
        #     try:
        #         session = await self.sio.get_session(sid)
        #         user_id = session.get('user_id')

        #         if not user_id:
        #             return  # Don't send error for read receipts

        #         # Mark message as read and notify sender
        #         message_id = data.get('message_id')
        #         sender_id = data.get('sender_id')
                
        #         if message_id and sender_id:
        #             read_data = {
        #                 "message_id": message_id,
        #                 "reader_id": user_id,
        #                 "timestamp": datetime.now().timestamp()
        #             }
                    
        #             # Notify the sender that their message was read
        #             await self.sio.emit('chat:read:confirmation', read_data, room=sender_id)
        #     except Exception as e:
        #         # Don't send errors for read receipts to avoid spam
        #         pass