from datetime import datetime
from typing import Annotated, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


# Custom type for handling ObjectId
def validate_object_id(v) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


# Define a type that uses the validator
PyObjectId = Annotated[ObjectId, BeforeValidator(validate_object_id)]


class MessageLog(BaseModel):
    """
    Represents a message in a chat room.

    Attributes:
        id: MongoDB ObjectId (automatically generated)
        room_id: ID of the room/conversation the message belongs to
        sender_id: User ID of the message sender
        content: Message text content
        timestamp: When the message was sent (defaults to current time)
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    room_id: str
    sender_id: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both alias and field name
        json_schema_extra={
            "example": {
                "room_id": "123",
                "sender_id": "123",
                "content": "Hello, this is a message!",
                "timestamp": "2023-01-01T12:00:00"
            }
        },
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    # For easier conversion to dict with string ID
    def model_dump_json_friendly(self):
        """
        Convert the model to a JSON-friendly dictionary with string ObjectId.
        """
        data = self.model_dump(by_alias=True)
        if data.get("_id"):
            data["_id"] = str(data["_id"])
        return data
