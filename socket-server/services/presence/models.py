# services/presence/models.py
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class StatusType(str, Enum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class UserStatus(BaseModel):
    """Represents a user's online status"""
    user_id: str
    status: StatusType = StatusType.OFFLINE
    last_changed: datetime = Field(default_factory=datetime.now)

    def update_status(self, new_status: StatusType) -> "UserStatus":
        """Update the user status and timestamp"""
        self.status = new_status
        self.last_changed = datetime.now()
        return self
