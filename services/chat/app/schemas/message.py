from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MessageBase(BaseModel):
    """Base schema for message"""
    content: str = Field(..., description="Content of the message")
    chat_id: str = Field(...,
                         description="ID of the chat this message belongs to")


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    pass


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: str = Field(..., description="Message ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    sender_id: str = Field(...,
                           description="ID of the user who sent the message")
    is_edited: bool = Field(
        False, description="Whether the message has been edited")

    class Config:
        orm_mode = True


class MessageListResponse(BaseModel):
    """Schema for list of messages"""
    messages: List[MessageResponse] = Field(...,
                                            description="List of messages")
