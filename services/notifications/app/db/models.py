from pydantic import BaseModel, Field, field_validator, model_validator
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class DeliveryType(str, Enum):
    """Enum for notification delivery types."""
    DELIVERED = "delivered"
    UNDELIVERED = "undelivered"
    ERROR = "error"


class NotificationType(str, Enum):
    """Enum for notification types."""
    MESSAGE = "message"
    FRIEND_REQUEST = "friend_request"
    STATUS_UPDATE = "status_update"


# 1. API REQUEST MODEL - Accepts string IDs from client
class NotificationRequest(BaseModel):
    """API request model with string IDs."""
    recipient_id: str = Field(..., description="Recipient User ID")
    sender_id: str = Field(..., description="Sender User ID") 
    reference_id: str = Field(..., description="Reference ID (message_id or room_id)")
    content_preview: str = Field(default="Hello World!", description="Content preview")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Time the notification was sent")
    status: DeliveryType = Field(default=DeliveryType.UNDELIVERED, description="Delivery status")
    error: Optional[str] = Field(default=None, description="Error message if any")
    
    # Convert to DB model
    def to_db_model(self) -> 'NotificationDB':
        """Convert API request to database model with UUID conversion."""
        return NotificationDB(
            recipient_id=uuid.UUID(self.recipient_id),
            sender_id=uuid.UUID(self.sender_id),
            reference_id=uuid.UUID(self.reference_id),
            content_preview=self.content_preview,
            timestamp=self.timestamp,
            status=self.status,
            error=self.error,
            notification_type=NotificationType.MESSAGE,
            read=False
        )
    
    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

# 2. DATABASE MODEL - Uses UUID for internal storage
class NotificationDB(BaseModel):
    """Database model with UUID fields."""
    recipient_id: uuid.UUID = Field(..., description="Recipient User ID")
    sender_id: uuid.UUID = Field(..., description="Sender User ID")
    reference_id: uuid.UUID = Field(..., description="Reference ID (message_id or room_id)")
    content_preview: str = Field(default="Hello World!", description="Content preview")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Time sent")
    status: DeliveryType = Field(default=DeliveryType.UNDELIVERED, description="Delivery status")
    error: Optional[str] = Field(default=None, description="Error message if any")
    notification_type: NotificationType = Field(default=NotificationType.MESSAGE, description="Type")
    read: bool = Field(default=False, description="Whether notification has been read")
    
    # Convert to MongoDB-compatible dictionary
    def to_mongo_dict(self) -> dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump()
        # Convert UUID objects to strings
        for field in ['recipient_id', 'sender_id', 'reference_id']:
            if isinstance(data[field], uuid.UUID):
                data[field] = str(data[field])
        return data
    
    # Convert to API response
    def to_api_response(self) -> 'NotificationResponse':
        """Convert to API response model."""
        return NotificationResponse(
            recipient_id=str(self.recipient_id),
            sender_id=str(self.sender_id),
            reference_id=str(self.reference_id),
            content_preview=self.content_preview,
            timestamp=self.timestamp,
            status=self.status,
            error=self.error,
            read=self.read,
            notification_type=self.notification_type
        )
    
    # Create from MongoDB document
    @classmethod
    def from_mongo_doc(cls, doc: dict[str, Any]) -> 'NotificationDB':
        """Create from MongoDB document."""
        # Convert string IDs back to UUIDs
        for field in ['recipient_id', 'sender_id', 'reference_id']:
            if field in doc and isinstance(doc[field], str):
                try:
                    doc[field] = uuid.UUID(doc[field])
                except ValueError:
                    # Handle invalid UUIDs
                    doc[field] = uuid.uuid4()
        
        return cls(**doc)

# 3. API RESPONSE MODEL - Returns string IDs to client
class NotificationResponse(BaseModel):
    """API response model with string IDs."""
    notification_id: Optional[str] = Field(default=None, description="Notification ID")
    recipient_id: str = Field(..., description="Recipient User ID")
    sender_id: str = Field(..., description="Sender User ID")
    reference_id: str = Field(..., description="Reference ID")
    content_preview: str = Field(default="Hello World!", description="Content preview")
    timestamp: str = Field(..., description="Time sent")
    status: DeliveryType = Field(..., description="Delivery status")
    error: Optional[str] = Field(default=None, description="Error message")
    read: bool = Field(default=False, description="Whether notification has been read")
    notification_type: NotificationType = Field(..., description="Type of notification")


class JWTTokenData(BaseModel):
    """JWT token payload structure that uses user_id as the subject."""
    user_id: uuid.UUID  # UUID of the user (will be encoded as string in JWT)
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
    def validate_user_id(cls, v: uuid.UUID) -> uuid.UUID:
        """Ensure user_id is a UUID - convert from string if needed"""
        if isinstance(v, str):
            return uuid.UUID(v)
        return v

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")