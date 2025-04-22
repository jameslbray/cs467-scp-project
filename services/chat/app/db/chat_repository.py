from typing import List, Optional
from app.models.chat import Chat
from app.schemas.chat import ChatCreate
from app.db.repository import Repository
from app.db.mongo import get_db


class ChatRepository(Repository[Chat, ChatCreate, ChatCreate]):
    """Repository for chat operations"""

    def __init__(self):
        """Initialize the chat repository"""
        super().__init__(Chat, "chats")

    async def get(self, id: str) -> Optional[Chat]:
        """
        Get a chat by ID

        Args:
            id: The ID of the chat

        Returns:
            The chat if found, None otherwise
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        chat_data = await db[self.collection_name].find_one({"_id": id})
        if not chat_data:
            return None

        return Chat(**chat_data)

    async def get_all(self) -> List[Chat]:
        """
        Get all chats

        Returns:
            A list of all chats
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        chats = []
        async for chat_data in db[self.collection_name].find():
            chats.append(Chat(**chat_data))

        return chats

    async def create(self, obj_in: ChatCreate) -> Chat:
        """
        Create a new chat

        Args:
            obj_in: The chat to create

        Returns:
            The created chat
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        now = self.get_current_time()
        chat_id = self.generate_id()

        chat_data = {
            "_id": chat_id,
            "name": obj_in.name,
            "description": obj_in.description,
            "is_private": obj_in.is_private,
            "created_at": now,
            "updated_at": now,
            "created_by": obj_in.created_by,
            "participant_ids": obj_in.participant_ids
        }

        await db[self.collection_name].insert_one(chat_data)

        return Chat(**chat_data)

    async def update(self, id: str, obj_in: ChatCreate) -> Optional[Chat]:
        """
        Update a chat

        Args:
            id: The ID of the chat to update
            obj_in: The chat with updated values

        Returns:
            The updated chat if found, None otherwise
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        chat = await self.get(id)
        if not chat:
            return None

        update_data = {
            "name": obj_in.name,
            "description": obj_in.description,
            "is_private": obj_in.is_private,
            "updated_at": self.get_current_time(),
            "participant_ids": obj_in.participant_ids
        }

        await db[self.collection_name].update_one(
            {"_id": id},
            {"$set": update_data}
        )

        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """
        Delete a chat

        Args:
            id: The ID of the chat to delete

        Returns:
            True if the chat was deleted, False otherwise
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        result = await db[self.collection_name].delete_one({"_id": id})
        return result.deleted_count > 0

    async def get_user_chats(self, user_id: str) -> List[Chat]:
        """
        Get all chats for a user

        Args:
            user_id: The ID of the user

        Returns:
            A list of chats the user is in
        """
        db = get_db()
        if not db:
            raise RuntimeError("Database not initialized")

        chats = []
        async for chat_data in db[self.collection_name].find(
            {"participant_ids": user_id}
        ):
            chats.append(Chat(**chat_data))

        return chats
