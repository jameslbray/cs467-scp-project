# import json
import asyncpg
import logging
# import aioredis

from .models import UserStatus  # , StatusType


class StatusRepository:
    """Repository for managing user status data in PostgreSQL and Redis"""

    def __init__(self, config: dict):
        """Initialize the repository with connection configs"""
        self.pg_config = config["postgres"]
        # self.redis_config = config["redis"]
        # self.redis_key_prefix = "user:status:"
        self.pg_pool = None
        # self.redis = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize database connections"""
        # Create PostgreSQL connection pool
        self.pg_pool = await asyncpg.create_pool(**self.pg_config)

        # Create Redis connection
        # self.redis = await aioredis.create_redis_pool(
        #     f"redis://{self.redis_config['host']}:{self.redis_config['port']}",
        #     password=self.redis_config.get("password")
        # )

        self.logger.info("Status repository initialized")

    async def get_user_status(self, user_id: str) -> UserStatus | None:
        """Get a user's status, trying cache first then database"""
        try:
            # # Try Redis first for performance
            # cached_status = await self.redis.get(
            # self.redis_key_prefix + user_id)

            # if cached_status:
            #     status_data = json.loads(cached_status)
            #     return UserStatus(
            #         user_id=user_id,
            #         status=status_data["status"],
            #         last_changed=status_data["last_changed"]
            #     )

            # Fallback to PostgreSQL
            row = await self.pg_pool.fetchrow(
                """SELECT status, last_status_change
                FROM user_status WHERE user_id = $1""",
                user_id
            )

            if not row:
                return None

            db_status = UserStatus(
                user_id=user_id,
                status=row["status"],
                last_changed=row["last_status_change"]
            )

            # # Cache the result for next time
            # await self.redis.set(
            #     self.redis_key_prefix + user_id,
            #     json.dumps(db_status.dict()),
            #     expire=300  # Cache for 5 minutes
            # )

            return db_status

        except Exception as e:
            self.logger.error(f"Error fetching user status: {e}")
            raise

    async def update_user_status(self, user_status: UserStatus) -> bool:
        """Update status in both cache and database"""
        try:
            # Update PostgreSQL for persistence
            await self.pg_pool.execute(
                """
                INSERT INTO user_status (user_id, status, last_status_change)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET status = $2, last_status_change = $3
                """,
                user_status.user_id,
                user_status.status.value,
                user_status.last_changed
            )

            # # Update Redis for real-time access
            # await self.redis.set(
            #     self.redis_key_prefix + user_status.user_id,
            #     json.dumps(user_status.dict()),
            #     expire=300  # Cache for 5 minutes
            # )

            return True

        except Exception as e:
            self.logger.error(f"Error updating user status: {e}")
            raise

    async def get_bulk_user_statuses(
        self, user_ids: list[str]
    ) -> dict[str, UserStatus]:
        """Get statuses for multiple users efficiently"""
        result = {}

        # # First try Redis pipeline for bulk retrieval
        # pipe = self.redis.pipeline()
        # for user_id in user_ids:
        #     pipe.get(self.redis_key_prefix + user_id)

        # cached_results = await pipe.execute()

        # Process cache hits
        # use this to get the cached results from redis if we use redis
        # missing_ids = []
        # for i, (user_id, cached) in enumerate(zip(user_ids, cached_results)):
        #     if cached:
        #         status_data = json.loads(cached)
        #         result[user_id] = UserStatus(
        #             user_id=user_id,
        #             status=status_data["status"],
        #             last_changed=status_data["last_changed"]
        #         )
        #     else:
        #         missing_ids.append(user_id)

        # for user_id in user_ids:
        #     missing_ids.append(user_id)

        # If we have missing ids, query database
        # if missing_ids:
        #     rows = await self.pg_pool.fetch(
        #         """
        #         SELECT user_id, status, last_status_change
        #         FROM user_status
        #         WHERE user_id = ANY($1)
        #         """,
        #         missing_ids
        #     )
        if user_ids:
            rows = await self.pg_pool.fetch(
                """
                SELECT user_id, status, last_status_change
                FROM user_status
                WHERE user_id = ANY($1)
                """,
                user_ids
            )

            # # Add results to cache and result dict
            # pipe = self.redis.pipeline()
            for row in rows:
                db_status = UserStatus(
                    user_id=row["user_id"],
                    status=row["status"],
                    last_changed=row["last_status_change"]
                )

                result[row["user_id"]] = db_status

            #     # Add to cache
            #     pipe.set(
            #         self.redis_key_prefix + row["user_id"],
            #         json.dumps(db_status.dict()),
            #         expire=300
            #     )

            # await pipe.execute()

        return result

    async def close(self) -> None:
        """Close database connections"""
        if self.pg_pool:
            await self.pg_pool.close()

        # if self.redis:
        #     self.redis.close()
        #     await self.redis.wait_closed()
