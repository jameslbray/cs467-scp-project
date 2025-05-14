from typing import Generic, TypeVar, Type, List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

# Define generic types
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class Repository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository class for database operations"""

    def __init__(self, model: Type[ModelType], collection_name: str):
        """
        Initialize the repository

        Args:
            model: The model class
            collection_name: The name of the collection in the database
        """
        self.model = model
        self.collection_name = collection_name

    async def get(self, id: str) -> Optional[ModelType]:
        """
        Get a single record by ID

        Args:
            id: The ID of the record

        Returns:
            The record if found, None otherwise
        """
        # This is a placeholder - implement with actual database logic
        raise NotImplementedError("Subclasses must implement get()")

    async def get_all(self) -> List[ModelType]:
        """
        Get all records

        Returns:
            A list of all records
        """
        # This is a placeholder - implement with actual database logic
        raise NotImplementedError("Subclasses must implement get_all()")

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record

        Args:
            obj_in: The object to create

        Returns:
            The created object
        """
        # This is a placeholder - implement with actual database logic
        raise NotImplementedError("Subclasses must implement create()")

    async def update(self, id: str, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update a record

        Args:
            id: The ID of the record to update
            obj_in: The object with updated values

        Returns:
            The updated object if found, None otherwise
        """
        # This is a placeholder - implement with actual database logic
        raise NotImplementedError("Subclasses must implement update()")

    async def delete(self, id: str) -> bool:
        """
        Delete a record

        Args:
            id: The ID of the record to delete

        Returns:
            True if the record was deleted, False otherwise
        """
        # This is a placeholder - implement with actual database logic
        raise NotImplementedError("Subclasses must implement delete()")

    def generate_id(self) -> str:
        """
        Generate a unique ID

        Returns:
            A unique ID
        """
        return str(uuid.uuid4())

    def get_current_time(self) -> datetime:
        """
        Get the current time

        Returns:
            The current time
        """
        return datetime.now()
