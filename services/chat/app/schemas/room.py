from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoomBase(BaseModel):
    """Base schema for room"""

    name: str = Field(..., description="Name of the room")
    description: Optional[str] = Field(
        None, description="Description of the room"
    )
    is_private: bool = Field(False, description="Whether the room is private")
    max_participants: Optional[int] = Field(
        None, description="Maximum number of participants"
    )


class RoomCreate(RoomBase):
    """Schema for creating a room"""

    participant_ids: List[str] = Field(..., description="IDs of participants")
    created_by: str = Field(
        ..., description="ID of the user who created the room"
    )


class RoomResponse(RoomBase):
    """Schema for room response"""

    id: str = Field(..., description="Room ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(
        ..., description="ID of the user who created the room"
    )
    participant_count: int = Field(..., description="Number of participants")
    participant_ids: List[str] = Field(..., description="IDs of participants")

    class Config:
        orm_mode = True


class RoomListResponse(BaseModel):
    """Schema for list of rooms"""

    rooms: List[RoomResponse] = Field(..., description="List of rooms")
