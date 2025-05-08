from pydantic import BaseModel, Field, field_validator
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
    content_preview: str = Field(description="Content preview", default="Hello World!")
    timestamp: str = Field( decription="Time the notification was sent", default_factory=lambda: datetime.now().isoformat())
    
    def __getitem__(self, key):
        """Allow dictionary-like access: model['field_name']"""
        return getattr(self, key)
    
    def get(self, key, default=None):
        """Dictionary-like get method with default value."""
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

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


class DeliveryType(str, Enum):
    """Enum for notification delivery types."""
    DELIVERED = "delivered"
    UNDELIVERED = "undelivered"
    ERROR = "error"


class NotificationResponse(BaseNotification):
    """API response model."""
    # API-specific fields
    status: DeliveryType = Field(DeliveryType.UNDELIVERED, description="Delivery status")
    error: str | None = Field(None, description="Error message if any")


class NotificationRequest(BaseNotification):
    """API response model."""
    # API-specific fields
    status: DeliveryType = Field(DeliveryType.UNDELIVERED, description="Delivery status")
    error: str | None = Field(None, description="Error message if any")


class JWTTokenData(BaseModel):
    """JWT token payload structure that uses user_id as the subject."""
    user_id: UUID  # UUID of the user (will be encoded as string in JWT)
    exp: Optional[datetime] = None  # Expiration time
    iat: Optional[datetime] = None  # Issued at time
    jti: Optional[str] = None  # JWT ID for token identification/revocation

    @field_validator("jti", mode="before")
    @classmethod
    def default_jti(cls, v: Optional[str]) -> str:
        """Generate a random UUID for the token ID if not provided"""
        return v or str(uuid.uuid4())
    
    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        """Ensure user_id is a UUID - convert from string if needed"""
        if isinstance(v, str):
            return uuid.UUID(v)
        return v

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")