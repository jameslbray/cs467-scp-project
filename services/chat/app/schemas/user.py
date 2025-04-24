from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base schema for user"""

    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(True, description="Whether the user is active")


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(..., description="Password")


class UserResponse(UserBase):
    """Schema for user response"""

    id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        orm_mode = True


class UserListResponse(BaseModel):
    """Schema for list of users"""

    users: List[UserResponse] = Field(..., description="List of users")
