from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message domain model"""

    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Content of the message")
    chat_id: str = Field(..., description="ID of the chat this message belongs to")
    sender_id: str = Field(..., description="ID of the user who sent the message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_edited: bool = Field(False, description="Whether the message has been edited")

    def edit(self, new_content: str) -> None:
        """Edit the message content"""
        self.content = new_content
        self.updated_at = datetime.now()
        self.is_edited = True

    def is_from_user(self, user_id: str) -> bool:
        """Check if the message is from a specific user"""
        return self.sender_id == user_id
