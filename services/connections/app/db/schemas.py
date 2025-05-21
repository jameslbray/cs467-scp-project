from pydantic import BaseModel, Field, field_validator, model_validator
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class ConnectionStatus(str, Enum):
    """Enum for connection status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class Connection(BaseModel):
    id: Optional[uuid.UUID] = Field(None, description="Unique identifier for the connection")
    user_id: uuid.UUID = Field(..., description="ID of the user initiating the connection")
    friend_id: uuid.UUID = Field(..., description="ID of the user being connected to")
    status: ConnectionStatus = Field(default=ConnectionStatus.PENDING, description="Status of the connection")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }


class ConnectionCreate(BaseModel):
    user_id: uuid.UUID = Field(..., description="ID of the user initiating the connection")
    friend_id: uuid.UUID = Field(..., description="ID of the user being connected to")
    status: ConnectionStatus = Field(default=ConnectionStatus.PENDING, description="Status of the connection")


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

class ConnectionUpdate(BaseModel):
    """Model for updating a connection."""
    id: Optional[uuid.UUID] = Field(None, description="ID of the connection to update")
    user_id: uuid.UUID = Field(..., description="ID of the user initiating the connection")
    friend_id: uuid.UUID = Field(..., description="ID of the user being connected to")
    status: ConnectionStatus = Field(..., description="New status of the connection")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
