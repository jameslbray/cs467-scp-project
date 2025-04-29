# services/users/app/db/seeds/seed_users.py

import asyncio
from datetime import datetime

from sqlalchemy import insert

from app.db.session import async_session
from app.db.models import User, UserStatus


# --- Data to seed -----------------------------------------------------------

USERS = [
    {
        "username": "michael_shaffer",
        "created_at": datetime(2025, 1, 15, 8, 30),
        "updated_at": datetime(2025, 1, 15, 8, 30),
        "profile_picture_url": ("https://sycolibre.com/profiles/michael.jpg"),
        "last_login": datetime(2025, 4, 19, 14, 25),
    },
    {
        "username": "james_bray",
        "created_at": datetime(2025, 1, 16, 10, 15),
        "updated_at": datetime(2025, 1, 16, 10, 15),
        "profile_picture_url": ("https://sycolibre.com/profiles/james.jpg"),
        "last_login": datetime(2025, 4, 20, 9, 15),
    },
    {
        "username": "charles_holz",
        "created_at": datetime(2025, 1, 17, 14, 45),
        "updated_at": datetime(2025, 1, 17, 14, 45),
        "profile_picture_url": ("https://sycolibre.com/profiles/charles.jpg"),
        "last_login": datetime(2025, 4, 18, 18, 30),
    },
    {
        "username": "nicholas_laustrup",
        "created_at": datetime(2025, 1, 18, 12, 20),
        "updated_at": datetime(2025, 1, 18, 12, 20),
        "profile_picture_url": ("https://sycolibre.com/profiles/nicholas.jpg"),
        "last_login": datetime(2025, 4, 19, 20, 45),
    },
]

USER_STATUSES = [
    {
        "user_id": 1,
        "status": "online",
        "last_status_change": datetime(2025, 4, 19, 14, 25),
    },
    {
        "user_id": 2,
        "status": "online",
        "last_status_change": datetime(2025, 4, 20, 9, 15),
    },
    {
        "user_id": 3,
        "status": "away",
        "last_status_change": datetime(2025, 4, 18, 19, 45),
    },
    {
        "user_id": 4,
        "status": "offline",
        "last_status_change": datetime(2025, 4, 19, 21, 30),
    },
]


# --- Seed function ----------------------------------------------------------


async def seed_users() -> None:
    """
    Insert initial users and their statuses into the database.
    """
    async with async_session() as session:
        async with session.begin():
            # Bulk insert into users
            await session.execute(insert(User).values(USERS))
            # Bulk insert into user_status
            await session.execute(insert(UserStatus).values(USER_STATUSES))
    print("✅ Seeded users and user_status tables.")


# --- CLI entry point --------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(seed_users())
