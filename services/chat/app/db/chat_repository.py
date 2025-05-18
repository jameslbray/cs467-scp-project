from typing import List, Optional

from ..models.message import Message
from ..models.room import Room
from ..schemas.room import RoomCreate
from .mongo import get_db
from .repository import Repository


class ChatRepository(Repository[Room, RoomCreate, RoomCreate]):
    """Repository for room operations"""

    def __init__(self):
        """Initialize the room repository"""
        super().__init__(Room, "rooms")

    async def get_room_by_id(self, id: str) -> Optional[Room]:
        """
        Get a room by ID

        Args:
            id: The ID of the room

        Returns:
            The room if found, None otherwise
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        room_data = await db[self.collection_name].find_one({"_id": id})
        if not room_data:
            return None

        return Room(**room_data)

    async def get_room_id_by_name(self, name: str) -> Optional[str]:
        """
        Get a room by name

        Args:
            name: The name of the room
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        room_data = await db[self.collection_name].find_one({"name": name})
        if not room_data:
            return None

        return room_data["_id"]

    async def get_all_rooms(self) -> List[Room]:
        """
        Get all rooms

        Returns:
            A list of all rooms
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        rooms = []
        async for room_data in db[self.collection_name].find():
            rooms.append(Room(**room_data))

        return rooms

    async def create(self, obj_in: RoomCreate) -> Room:
        """
        Create a new room

        Args:
            obj_in: The room to create

        Returns:
            The created room
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        now = self.get_current_time()
        room_id = self.generate_id()

        room_data = {
            "_id": room_id,
            "name": obj_in.name,
            "description": obj_in.description,
            "is_private": obj_in.is_private,
            "max_participants": obj_in.max_participants,
            "created_at": now,
            "updated_at": now,
            "created_by": getattr(obj_in, "created_by", None),
            "participant_ids": getattr(obj_in, "participant_ids", []),
        }

        await db[self.collection_name].insert_one(room_data)

        return Room(**room_data)

    async def update(self, id: str, obj_in: RoomCreate) -> Optional[Room]:
        """
        Update a room

        Args:
            id: The ID of the room to update
            obj_in: The room with updated values

        Returns:
            The updated room if found, None otherwise
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        room = await self.get_room_by_id(id)
        if not room:
            return None

        update_data = {
            "name": obj_in.name,
            "description": obj_in.description,
            "is_private": obj_in.is_private,
            "max_participants": obj_in.max_participants,
            "updated_at": self.get_current_time(),
            "participant_ids": getattr(obj_in, "participant_ids", []),
        }

        await db[self.collection_name].update_one(
            {"_id": id}, {"$set": update_data}
        )

        return await self.get_room_by_id(id)

    async def delete(self, id: str) -> bool:
        """
        Delete a room

        Args:
            id: The ID of the room to delete

        Returns:
            True if the room was deleted, False otherwise
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        result = await db[self.collection_name].delete_one({"_id": id})
        return result.deleted_count > 0

    async def get_user_rooms(self, user_id: str) -> List[Room]:
        """
        Get all rooms for a user

        Args:
            user_id: The ID of the user

        Returns:
            A list of rooms the user is in
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        rooms = []
        async for room_data in db[self.collection_name].find(
            {"participant_ids": user_id}
        ):
            rooms.append(Room(**room_data))

        return rooms

    async def add_user_to_room(
        self, room_id: str, user_id: str
    ) -> Optional[Room]:
        """
        Add a user to the participant_ids of a room.
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        # Use $addToSet to avoid duplicates
        result = await db[self.collection_name].update_one(
            {"_id": room_id},
            {
                "$addToSet": {"participant_ids": user_id},
                "$set": {"updated_at": self.get_current_time()},
            },
        )
        if result.modified_count == 0:
            # Room not found or user already present
            return None
        return await self.get_room_by_id(room_id)

    async def get_messages(
        self, room_id: str, skip: int, limit: int
    ) -> List[Message]:
        """
        Get messages for a specific room

        Args:
            room_id: The ID of the room
            skip: The number of messages to skip
            limit: The number of messages to return

        Returns:
            A list of messages
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")

        messages = []
        cursor = (
            db.messages.find({"room_id": room_id})
            .skip(skip)
            .limit(limit)
            .sort("created_at", 1)
        )
        async for message_data in cursor:
            messages.append(Message(**message_data))
        return messages

    async def get_room_users(self, room_id: str) -> List[str]:
        """
        Get all users in a room
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database not initialized")
        room = await db[self.collection_name].find_one(
            {"_id": room_id}, {"participant_ids": 1}
        )
        if not room:
            return []
        return room["participant_ids"]

    async def is_user_member(self, room_id: str, user_id: str) -> bool:
        """
        Check if a user is a member of a room
        """
        users = await self.get_room_users(room_id)
        return user_id in users
