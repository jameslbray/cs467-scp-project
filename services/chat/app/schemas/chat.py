from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatBase(BaseModel):
    """Base schema for chat"""

    name: str = Field(..., description="Name of the chat")
    description: Optional[str] = Field(None, description="Description of the chat")
    is_private: bool = Field(False, description="Whether the chat is private")


class ChatCreate(ChatBase):
    """Schema for creating a chat"""

    participant_ids: List[str] = Field(..., description="IDs of participants")


class ChatResponse(ChatBase):
    """Schema for chat response"""

    id: str = Field(..., description="Chat ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="ID of the user who created the chat")
    participant_ids: List[str] = Field(..., description="IDs of participants")

    class Config:
        orm_mode = True


class ChatListResponse(BaseModel):
    """Schema for list of chats"""

    chats: List[ChatResponse] = Field(..., description="List of chats")
