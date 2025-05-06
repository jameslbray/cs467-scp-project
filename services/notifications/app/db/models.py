from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Optional


class BaseNotification(BaseModel):
    """Base notification model with common fields."""
    notification_id: str = Field(..., description="Notification ID", default_factory=lambda: str(UUID(int=0)))
    recipient_id: str = Field(..., description="Recipient User ID", default_factory=lambda: str(UUID(int=0)))
    sender_id: str = Field(..., description="Sender User ID", default_factory=lambda: str(UUID(int=0)))
    reference_id: str = Field(..., description="Reference ID (message_id or room_id)", default_factory=lambda: str(UUID(int=0)))
    content_preview: str = Field(default_factory=str, description="Content preview", default="Hello World!")
    timestamp: str = Field( decription="Time the notification was sent", default_factory=lambda: datetime.now().isoformat())

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }


class NotificationType(str, Enum):
    """Enum for notification types."""
    MESSAGE = "message"
    FRIEND_REQUEST = "friend_request"
    STATUS_UPDATE = "status_update"


class UserNotification(BaseNotification):
    """Internal notification model with additional fields."""
    read: bool = Field(False, description="Whether notification has been read")
    notification_type: NotificationType = Field(NotificationType.MESSAGE, description="Type of notification")


class NotificationResponse(BaseNotification):
    """API response model."""
    # API-specific fields
    status: str = Field("undelivered", description="Delivery status")
    error: str | None = Field(None, description="Error message if any")


class NotificationRequest(BaseNotification):
    """API response model."""
    # API-specific fields
    status: str = Field("undelivered", description="Delivery status")
    error: str | None = Field(None, description="Error message if any")
