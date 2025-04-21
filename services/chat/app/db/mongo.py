# services/chat/app/db/mongo.py

import os
import motor.motor_asyncio
from pydantic import BaseSettings


class MongoSettings(BaseSettings):
    uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name: str = os.getenv("MONGO_DB", "chat_db")


settings = MongoSettings()

client: motor.motor_asyncio.AsyncIOMotorClient | None = None
db = None


def init_mongo() -> None:
    """Called on FastAPI startup to initialize the client."""
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.uri)
    db = client[settings.db_name]
