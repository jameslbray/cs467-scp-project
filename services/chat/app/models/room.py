from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Room(BaseModel):
    """Room domain model"""

    id: str = Field(..., description="Room ID")
    display_name: str = Field(..., description="Name of the room")
    description: Optional[str] = Field(
        None, description="Description of the room")
    is_private: bool = Field(False, description="Whether the room is private")
    max_participants: Optional[int] = Field(
        None, description="Maximum number of participants"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(...,
                            description="ID of the user who created the room")
    participant_ids: List[str] = Field(
        default_factory=list, description="IDs of participants"
    )

    def add_participant(self, user_id: str) -> bool:
        """Add a participant to the room"""
        if (
            self.max_participants is not None
            and len(self.participant_ids) >= self.max_participants
        ):
            return False

        if user_id not in self.participant_ids:
            self.participant_ids.append(user_id)
            self.updated_at = datetime.now()
            return True
        return False

    def remove_participant(self, user_id: str) -> bool:
        """Remove a participant from the room"""
        if user_id in self.participant_ids:
            self.participant_ids.remove(user_id)
            self.updated_at = datetime.now()
            return True
        return False

    def is_participant(self, user_id: str) -> bool:
        """Check if a user is a participant in the room"""
        return user_id in self.participant_ids

    def get_participant_count(self) -> int:
        """Get the number of participants in the room"""
        return len(self.participant_ids)
