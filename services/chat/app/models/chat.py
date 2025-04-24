from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Chat(BaseModel):
    """Chat domain model"""

    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Name of the chat")
    description: Optional[str] = Field(None, description="Description of the chat")
    is_private: bool = Field(False, description="Whether the chat is private")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="ID of the user who created the chat")
    participant_ids: List[str] = Field(..., description="IDs of participants")

    def add_participant(self, user_id: str) -> None:
        """Add a participant to the chat"""
        if user_id not in self.participant_ids:
            self.participant_ids.append(user_id)
            self.updated_at = datetime.now()

    def remove_participant(self, user_id: str) -> bool:
        """Remove a participant from the chat"""
        if user_id in self.participant_ids:
            self.participant_ids.remove(user_id)
            self.updated_at = datetime.now()
            return True
        return False

    def is_participant(self, user_id: str) -> bool:
        """Check if a user is a participant in the chat"""
        return user_id in self.participant_ids
