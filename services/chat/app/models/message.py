from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message domain model"""

    id: str = Field(..., alias="_id")
    room_id: str
    sender_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool = False

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def edit(self, new_content: str) -> None:
        """Edit the message content"""
        self.content = new_content
        self.updated_at = datetime.now()
        self.is_edited = True

    def is_from_user(self, user_id: str) -> bool:
        """Check if the message is from a specific user"""
        return self.sender_id == user_id
