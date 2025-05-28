import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class UserStatusEnum(str, Enum):
    """Enum for user status values"""

    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class UserStatusBase(BaseModel):
    """Base schema for user status"""

    status: UserStatusEnum
    last_status_change: Optional[datetime] = None


class UserStatusCreate(UserStatusBase):
    """Schema for creating user status"""

    pass


class UserStatusSchema(UserStatusBase):
    """Schema for user status responses"""

    user_id: UUID

    class Config:
        from_attributes = True


class User(BaseModel):
    """Base schema for user data"""

    username: str
    email: EmailStr
    display_name: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserCreate(User):
    """Schema for creating a new user"""

    password: str

class UserUpdate(BaseModel):
    """Schema for modifying a user"""

    email: EmailStr
    profile_picture_url: str

class UserSchema(User):
    """Schema for user responses, including relationships"""

    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    status: Optional[UserStatusSchema] = None
    # Note: We don't include connections/friends here to avoid circular references
    # They should be fetched separately through the connections service

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication tokens"""

    access_token: str
    token_type: str
    expires_at: datetime


class JWTTokenData(BaseModel):
    """JWT token payload structure that uses user_id as the subject"""

    user_id: UUID
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

    @field_validator("jti", mode="before")
    @classmethod
    def default_jti(cls, v: Optional[str]) -> str:
        return v or str(uuid.uuid4())

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        if isinstance(v, str):
            return uuid.UUID(v)
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset requests"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for confirming password resets"""

    token: str
    new_password: str


class PasswordResetTokenSchema(BaseModel):
    """Schema for password reset tokens"""

    id: int
    user_id: UUID
    token: str
    expires_at: datetime

    class Config:
        from_attributes = True


class BlacklistedTokenSchema(BaseModel):
    """Schema for blacklisted tokens"""

    id: UUID
    token: str
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    blacklisted_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True
