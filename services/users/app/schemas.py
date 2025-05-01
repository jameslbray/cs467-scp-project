from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID  # Import UUID type
from typing import Optional
from datetime import datetime
import uuid

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: UUID  # Change from int to UUID
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


class TokenData(BaseModel):
    username: Optional[str] = None


class JWTTokenData(BaseModel):
    username: Optional[str] = None
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

    @field_validator("jti", mode="before")
    @classmethod
    def default_jti(cls, v: Optional[str]) -> str:
        """Generate a random UUID for the token ID if not provided"""
        return v or str(uuid.uuid4())
