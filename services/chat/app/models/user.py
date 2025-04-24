from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """User domain model"""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(True, description="Whether the user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    chat_ids: List[str] = Field(
        default_factory=list, description="IDs of chats the user is in"
    )

    def update_last_login(self) -> None:
        """Update the last login timestamp"""
        self.last_login = datetime.now()
        self.updated_at = datetime.now()

    def add_chat(self, chat_id: str) -> None:
        """Add a chat to the user's chat list"""
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            self.updated_at = datetime.now()

    def remove_chat(self, chat_id: str) -> bool:
        """Remove a chat from the user's chat list"""
        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            self.updated_at = datetime.now()
            return True
        return False

    def is_in_chat(self, chat_id: str) -> bool:
        """Check if the user is in a specific chat"""
        return chat_id in self.chat_ids
