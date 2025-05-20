import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID  # Import UUID type

from pydantic import BaseModel, EmailStr, field_validator


class User(BaseModel):
    username: str
    email: EmailStr


class UserCreate(User):
    password: str


class User(User):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


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


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
