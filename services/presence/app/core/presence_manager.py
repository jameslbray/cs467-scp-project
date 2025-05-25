"""
Presence manager for handling user presence state.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import asyncpg  # type: ignore
from enum import Enum
from uuid import UUID
from services.shared.utils.retry import CircuitBreaker, with_retry
from services.rabbitmq.core.client import RabbitMQClient

# configure logging
logger = logging.getLogger(__name__)


class StatusType(str, Enum):
    """User status types."""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"
    INVISIBLE = "invisible"


class UserStatus:
    """User status model."""

    def __init__(
        self,
        user_id: str,
        status: StatusType,
        last_status_change: Optional[float] = None
    ):
        try:
            # Convert string to UUID if it's not already
            self.user_id = UUID(user_id) if isinstance(
                user_id, str) else user_id
        except ValueError:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            raise
        self.status = status
        self.last_status_change = last_status_change or datetime.now().timestamp()

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),  # Convert UUID to string for JSON
            "status": self.status.value,
            "last_status_change": self.last_status_change,
        }


class PresenceManager:
    """Manages user presence state."""

    def __init__(
        self,
        config: Dict[str, Any],
        # socket_server: Optional[SocketManager] = None
    ):
        """Initialize the presence manager.

        Args:
            config: Configuration dictionary containing RabbitMQ settings
            socket_server: Optional Socket.IO server instance
        """
        self.config = config
        self._initialized = False
        self.db_pool: Optional[asyncpg.Pool] = None
        # self.socket_server = socket_server

        # User presence data
        self.presence_data: dict[str, dict[str, Any]] = {}

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()

        # Initialize circuit breakers
        self.rabbitmq_cb = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30.0
        )
        self.db_cb = CircuitBreaker(
            "postgres",
            failure_threshold=3,
            reset_timeout=30.0
        )

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()

        # Initialize circuit breakers
        self.rabbitmq_cb = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30.0
        )
        self.db_cb = CircuitBreaker(
            "postgres",
            failure_threshold=3,
            reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the presence manager."""
        if self._initialized:
            logger.warning("Presence manager already initialized")
            return

        try:
            # Initialize RabbitMQ client with circuit breaker
            await with_retry(
                self._connect_rabbitmq,
                max_attempts=5,
                initial_delay=5.0,
                max_delay=60.0,
                circuit_breaker=self.rabbitmq_cb
            )

            # Initialize database if this is the presence service
            if "postgres" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb
                )

            self._initialized = True
            logger.info("Presence manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize presence manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the presence manager."""
        await self.rabbitmq.close()

        if self.db_pool:
            await self.db_pool.close()

        logger.info("Presence manager shut down")

    async def _connect_database(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            # Connect to PostgreSQL
            config = self.config["postgres"].copy()
            if "options" in config:
                # Remove options as it's not supported by asyncpg
                del config["options"]

            self.db_pool = await asyncpg.create_pool(
                min_size=2,
                max_size=10,
                **config
            )
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def _connect_rabbitmq(self) -> None:
        """Connect to RabbitMQ."""
        try:
            # Connect to RabbitMQ using the shared client
            connected = await self.rabbitmq.connect()
            if not connected:
                raise Exception("Failed to connect to RabbitMQ")

            # Declare exchange
            await self.rabbitmq.declare_exchange("user", "topic")

            # Declare and bind queue
            await self.rabbitmq.declare_queue(
                "presence_updates",
                durable=True
            )
            await self.rabbitmq.bind_queue(
                "presence_updates",
                "user",
                "status.#"
            )

            # Start consuming messages
            await self.rabbitmq.consume(
                "presence_updates",
                self._process_presence_message
            )

            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def check_connection_health(self):
        try:
            await self.db_pool.execute("SELECT 1")
            return True
        except Exception:
            logger.error("Postgres connection failed")
            return False
        
    async def _process_presence_message(self, message: Any) -> None:
        """Process a presence message from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            message_type = body.get("type")

            if message_type == "status_update":
                user_id = body.get("user_id")
                status = body.get("status")
                last_status_change = body.get("last_status_change")

                if user_id and status:
                    if self.db_pool:  # Only handle DB operations in presence service
                        await with_retry(
                            lambda: self._save_user_status(
                                user_id, StatusType(status), last_status_change),
                            max_attempts=3,
                            circuit_breaker=self.db_cb
                        )
                    else:  # Socket.IO service just updates in-memory state
                        self.presence_data[user_id] = {
                            "status": status,
                            "last_status_change": last_status_change or datetime.now().timestamp()
                        }

            elif message_type == "status_query":
                # Handle status queries through RabbitMQ
                if self.db_pool:
                    user_id = body.get("user_id")
                    status = await with_retry(
                        lambda: self._get_user_status(user_id),
                        max_attempts=3,
                        circuit_breaker=self.db_cb
                    )
                    # Publish status back
                    await with_retry(
                        lambda: self._publish_status_update(
                            user_id,
                            status.status if status else StatusType.OFFLINE
                        ),
                        max_attempts=3,
                        circuit_breaker=self.rabbitmq_cb
                    )

        except Exception as e:
            logger.error(f"Error processing presence message: {e}")
            await message.nack(requeue=False)
        else:
            await message.ack()

    async def _update_user_status(
        self,
        user_id: str,
        status: StatusType,
        last_status_change: Optional[float] = None
    ) -> bool:
        """Update a user's status.

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            status_type = status
            current_time = last_status_change or datetime.now().timestamp()

            # Initialize user in presence_data if not exists
            if user_id not in self.presence_data:
                self.presence_data[user_id] = {
                    "status": status_type.value,
                    "last_status_change": current_time
                }
                logger.info(f"Created new presence entry for user {user_id}")

            else:
                self.presence_data[user_id].update({
                    "status": status_type.value,
                    "last_status_change": last_status_change or datetime.now().timestamp()
                })

            # Update status in database and notify others
            await with_retry(
                lambda: self._save_user_status(
                    user_id,
                    status_type,
                    last_status_change
                ),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            # Publish status update to RabbitMQ
            await with_retry(
                lambda: self._publish_status_update(
                    user_id,
                    status_type,
                    last_status_change
                ),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb
            )

            # Notify friends
            await with_retry(
                lambda: self._notify_friends(user_id, status_type),
                max_attempts=3,
                circuit_breaker=self.rabbitmq_cb
            )

            logger.info(f"User {user_id} status updated to {status}")
            return True

        except ValueError:
            logger.error(f"Invalid status: {status}")
            return False

    async def _save_user_status(
        self,
        user_id: Union[str, int, UUID],
        status: StatusType,
        last_status_change: Optional[float] = None
    ) -> None:
        """Save user status to database.

        Args:
            user_id: User ID as string, int, or UUID
            status: User's status
            last_status_change: Timestamp of last status change
        """
        if not self.db_pool:
            logger.warning("Database pool not available")
            return

        try:
            last_status_change = last_status_change or datetime.now().timestamp()

            # Handle different user_id types
            if isinstance(user_id, str):
                try:
                    # Try to parse as UUID first
                    uuid_user_id = UUID(user_id)
                except ValueError:
                    # If not a valid UUID string, generate a v4 UUID
                    uuid_user_id = UUID(int=int(user_id)) if user_id.isdigit() \
                        else UUID(bytes=user_id.encode(), version=4)
                    logger.debug(
                        f"Generated UUID v4 from string: {user_id} -> {uuid_user_id}"
                    )
            elif isinstance(user_id, int):
                # For integers, we create a UUID v4 using the int value
                # This maintains consistency for the same integer input
                try:
                    uuid_user_id = UUID(int=user_id)
                except ValueError:
                    # If integer is too large, fall back to random UUID
                    uuid_user_id = UUID(
                        bytes=str(user_id).encode(),
                        version=4
                    )
                logger.debug(
                    f"Generated UUID v4 from int: {user_id} -> {uuid_user_id}"
                )
            elif isinstance(user_id, UUID):
                uuid_user_id = user_id
            else:
                raise ValueError(f"Unsupported user_id type: {type(user_id)}")

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO presence.presence (
                        user_id,
                        status,
                        last_status_change
                    ) VALUES ($1, $2, to_timestamp($3))
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        status = $2,
                        last_status_change = to_timestamp($3)
                    """,
                    str(uuid_user_id),  # Convert UUID to string for PostgreSQL
                    status.value,
                    last_status_change,
                )
        except Exception as e:
            logger.error(f"Failed to save user status: {e}")
            raise

    async def _publish_status_update(
        self,
        user_id: str,
        status: StatusType,
        last_status_change: Optional[float] = None
    ) -> None:
        """Publish status update to RabbitMQ."""
        try:
            message = json.dumps({
                "user_id": user_id,
                "status": status.value,
                "last_changed_status": last_status_change or datetime.now().timestamp(),
            })
            await self.rabbitmq.publish_message(
                exchange="user",
                routing_key=f"status.{user_id}",
                message=message
            )
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")
            raise

    async def _notify_friends(self, user_id: str, status: StatusType) -> None:
        """Notify friends about a user's status change."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return

        try:
            # Get friends with circuit breaker
            friends = await with_retry(
                lambda: self._get_friends(user_id),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            # Publish status update for each friend with circuit breaker
            for friend_id in friends:
                await with_retry(
                    lambda: self._publish_status_update(user_id, status),
                    max_attempts=3,
                    circuit_breaker=self.rabbitmq_cb
                )
        except Exception as e:
            logger.error(f"Failed to notify friends: {e}")
            raise

    async def _get_friends(self, user_id: str) -> List[str]:
        """Get a user's friends."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return []

        try:
            async with self.db_pool.acquire() as conn:
                # Query for accepted connections in both directions
                query = """
                    SELECT friend_id FROM connections.connections
                    WHERE user_id = $1 AND status = 'accepted'
                    UNION
                    SELECT user_id FROM connections.connections
                    WHERE friend_id = $1
                    AND status = 'accepted'
                """
                rows = await conn.fetch(query, user_id)

                # Extract friend IDs from results
                friend_ids = []
                for row in rows:
                    # Use the correct column name
                    friend_id = row["friend_id"] if "friend_id" in row else row["user_id"]
                    friend_ids.append(friend_id)
                return friend_ids
        except Exception as e:
            logger.error(f"Failed to get friends: {e}")
            return []

    async def _get_friend_ids(self, user_id: str) -> List[str]:
        """Get a user's friend IDs."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return []

        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT friend_id FROM connections.connections
                    WHERE user_id = $1 AND status = 'accepted'
                    UNION
                    SELECT user_id FROM connections.connections
                    WHERE friend_id = $1 AND status = 'accepted'
                """
                rows = await conn.fetch(query, user_id)
                return [str(row[0]) for row in rows]  # Convert to strings
        except Exception as e:
            logger.error(f"Failed to get friend IDs: {e}")
            return []

    async def _get_user_status(self, user_id: str) -> UserStatus | None:
        """Get user status from database."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return None

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT user_id, status, last_status_change
                    FROM presence.presence
                    WHERE user_id = $1
                """,
                    user_id,
                )

                if row:
                    return UserStatus(
                        user_id=str(row["user_id"]),  # Convert UUID to string
                        status=StatusType(row["status"]),
                        last_status_change=row["last_status_change"].timestamp(),
                    )
                return None
        except ValueError as e:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user status: {e}")
            return None

    async def get_user_status(self, user_id: str) -> dict[str, Any]:
        """Get user's current status."""
        # Default values
        default_status = {
            "status": StatusType.OFFLINE.value,
            "last_status_change": 0,
        }

        # Check cache first
        if user_id in self.presence_data:
            presence_data = self.presence_data[user_id]
            return {
                "status": presence_data.get("status", default_status["status"]),
                "last_status_change": presence_data.get("last_status_change", default_status["last_status_change"]),
            }

        # Fetch from database if not in cache
        user_status = await self._get_user_status(user_id)
        if user_status is None:
            return default_status

        return {
            "status": user_status.status.value,
            "last_status_change": user_status.last_status_change,
        }

    async def set_user_status(self, user_id: str, status: str, last_status_change: Optional[float] = None) -> bool:
        """Set user's status."""
        try:
            status_type = StatusType(status)
            current_time = last_status_change or datetime.now().timestamp()

            # Initialize user in presence_data if not exists
            if user_id not in self.presence_data:
                self.presence_data[user_id] = {
                    "status": status_type.value,
                    "last_status_change": current_time
                }
                logger.info(f"Created new presence entry for user {user_id}")

            else:
                self.presence_data[user_id].update({
                    "status": status_type.value,
                    "last_status_change": last_status_change or datetime.now().timestamp()
                })

            # Update status in database and notify others with circuit breaker
            await with_retry(
                lambda: self._update_user_status(user_id, status_type),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            logger.info(f"User {user_id} status set to {status}")
            return True
        except ValueError:
            logger.error(f"Invalid status: {status}")
            return False

    async def set_new_user_status(self, user_id: str) -> bool:
        """Set user's status."""
        try:
            status_type = StatusType.OFFLINE
            self.presence_data[user_id].update(
                {"status": status_type.value,
                 "last_status_change": datetime.now().timestamp()}
            )

            # Update status in database and notify others with circuit breaker
            await with_retry(
                lambda: self._save_user_status(user_id, status_type),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            logger.info(f"User {user_id} status set to {status}")
            return True
        except ValueError:
            logger.error(f"Invalid status: {status}")
            return False
