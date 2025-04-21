# services/chat/app/db/mongo_seeds.py

import asyncio
from datetime import datetime

from .mongo import db, init_mongo
from app.nosql_models.message_log import MessageLog

SAMPLE_LOGS = [
    {
        "room_id": 1,
        "sender_id": 10,
        "content": "Welcome to Room 1!",
        "timestamp": datetime(2025, 4, 20, 12, 0),
    },
    {
        "room_id": 1,
        "sender_id": 11,
        "content": "Hi there!",
        "timestamp": datetime(2025, 4, 20, 12, 1),
    },
]


async def seed_mongo() -> None:
    """
    Inserts sample documents into the message_logs collection.
    """
    init_mongo()
    # Drop existing for idempotence (dev only)
    await db.message_logs.drop()
    # Validate & insert
    docs = [MessageLog(**data).dict(by_alias=True) for data in SAMPLE_LOGS]
    result = await db.message_logs.insert_many(docs)
    print(f"✅ Inserted {len(result.inserted_ids)} message logs.")

if __name__ == "__main__":
    asyncio.run(seed_mongo())
