"""
Presence manager for handling user presence state.
"""

import logging
import json
import aio_pika
from typing import Dict, Any, Optional, List, TYPE_CHECKING, Never
from datetime import datetime
import asyncpg
from enum import Enum

if TYPE_CHECKING:
    # Import only for type checking to avoid circular imports
    from services.socket_io.app.core.socket_server import SocketServer as SocketManager
else:
    # Use a placeholder type at runtime
    SocketManager = Any  # This makes Python ignore the actual type at runtime

# Configure logging
logger = logging.getLogger(__name__)


class StatusType(str, Enum):
    """User status types."""

    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


class UserStatus:
    """User status model."""

    def __init__(self, user_id: str, status: StatusType,
                 last_changed: float = None):
        self.user_id = user_id
        self.status = status
        self.last_changed = last_changed or datetime.now().timestamp()

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "status": self.status.value,
            "last_changed": self.last_changed,
        }


class PresenceManager:
    """Manages user presence state."""

    def __init__(self, config: Dict[str, Any], socket_server: SocketManager = None):
        """Initialize the presence manager.

        Args:
            config: Configuration dictionary containing RabbitMQ and other
            settings
        """
        self.config = config
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.rabbitmq_exchange = None
        self._initialized = False
        self.db_pool = None if "postgres" not in config else None
        self.socket_server = socket_server

        # User presence data
        self.presence_data: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize the presence manager."""
        if self._initialized:
            logger.warning("Presence manager already initialized")
            return

        try:
            # Initialize RabbitMQ client
            await self._connect_rabbitmq()

            # Initialize database connection only if this is the presence service
            if "postgres" in self.config:
                await self._connect_database()

            self._initialized = True
            logger.info("Presence manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize presence manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the presence manager."""
        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()

        if self.db_pool:
            await self.db_pool.close()

        logger.info("Presence manager shut down")

    async def _connect_database(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            # Connect to PostgreSQL
            self.db_pool = await asyncpg.create_pool(
                min_size=2,
                max_size=10,
                **self.config["postgres"]
            )
            logger.info("Connected to PostgreSQL database")

            # Create tables if they don't exist
            async with self.db_pool.acquire() as conn:
                # Create user_status table
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_status (
                        user_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        last_changed TIMESTAMP NOT NULL
                    )
                """
                )

                # Create connections table
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS connections (
                        user_id TEXT NOT NULL,
                        connected_user_id TEXT NOT NULL,
                        connection_status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (user_id, connected_user_id)
                    )
                """
                )

            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def _connect_rabbitmq(self) -> None:
        """Connect to RabbitMQ."""
        try:
            # Connect to RabbitMQ
            self.rabbitmq_connection = await aio_pika.connect_robust(
                self.config["rabbitmq"]["url"]
            )

            # Create a channel
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()

            # Declare exchange
            self.rabbitmq_exchange = await (
                self.rabbitmq_channel.declare_exchange(
                    "user_events", aio_pika.ExchangeType.TOPIC, durable=True
                )
            )

            # Declare queue
            queue = await self.rabbitmq_channel.declare_queue(
                "presence_updates", durable=True
            )

            # Bind queue to exchange
            await queue.bind(self.rabbitmq_exchange, "status.#")

            # Start consuming messages
            await queue.consume(self._process_presence_message)

            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def _process_presence_message(
        self, message: aio_pika.IncomingMessage
    ) -> None:
        """Process a presence message from RabbitMQ."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                message_type = body.get("type")

                if message_type == "status_update":
                    user_id = body.get("user_id")
                    status = body.get("status")
                    last_changed = body.get("last_changed")

                    if user_id and status:
                        if self.db_pool:  # Only handle DB operations in presence service
                            await self._save_user_status(user_id, StatusType(status), last_changed)
                        else:  # Socket.IO service just updates in-memory state
                            self.presence_data[user_id] = {
                                "status": status,
                                "last_seen": last_changed or datetime.now().timestamp()
                            }

                elif message_type == "status_query":
                    # Handle status queries through RabbitMQ
                    if self.db_pool:
                        user_id = body.get("user_id")
                        status = await self._get_user_status(user_id)
                        # Publish status back
                        await self._publish_status_update(user_id, status.status if status else StatusType.OFFLINE)

            except Exception as e:
                logger.error(f"Error processing presence message: {e}")

    async def _update_user_status(
        self, user_id: str, status: StatusType, last_changed: float = None
    ) -> None:
        """Update a user's status."""
        # Update in-memory data
        if user_id in self.presence_data:
            self.presence_data[user_id].update(
                {
                    "status": status.value,
                    "last_seen": last_changed or datetime.now().timestamp(),
                }
            )

            # Save to database
            await self._save_user_status(user_id, status, last_changed)

            # Publish status update to RabbitMQ
            await self._publish_status_update(user_id, status, last_changed)

            # Notify friends
            await self._notify_friends(user_id, status)

    async def _save_user_status(
        self, user_id: str, status: StatusType, last_changed: float = None
    ) -> None:
        """Save user status to database."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return

        try:
            last_changed = last_changed or datetime.now().timestamp()
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_status (user_id, status, last_changed)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE
                    SET status = $2, last_changed = $3
                """,
                    user_id,
                    status.value,
                    last_changed,
                )
        except Exception as e:
            logger.error(f"Failed to save user status: {e}")

    async def _publish_status_update(
        self, user_id: str, status: StatusType, last_changed: float = None
    ) -> None:
        """Publish status update to RabbitMQ."""
        if not self.rabbitmq_exchange:
            logger.warning("RabbitMQ exchange not available")
            return

        try:
            message = aio_pika.Message(
                body=json.dumps(
                    {
                        "user_id": user_id,
                        "status": status.value,
                        "last_changed": last_changed
                        or datetime.now().timestamp(),  # type: ignore
                    }
                ).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self.rabbitmq_exchange.publish(
                message, routing_key=f"status.{user_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")

    async def _notify_friends(self, user_id: str, status: StatusType) -> None:
        """Notify friends about a user's status change."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return

        try:
            # Get friends
            friends = await self._get_friends(user_id)

            # Publish status update for each friend
            for friend_id in friends:
                await self._publish_status_update(user_id, status)
        except Exception as e:
            logger.error(f"Failed to notify friends: {e}")

    async def _get_friends(self, user_id: str) -> List[str]:
        """Get a user's friends."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return []

        try:
            async with self.db_pool.acquire() as conn:
                # Query for accepted connections in both directions
                query = """
                    SELECT connected_user_id FROM connections
                    WHERE user_id = $1 AND connection_status = 'accepted'
                    UNION
                    SELECT user_id FROM connections
                    WHERE connected_user_id = $1
                    AND connection_status = 'accepted'
                """
                rows = await conn.fetch(query, user_id)

                # Extract friend IDs from results
                friend_ids = []
                for row in rows:
                    friend_id = row["connected_user_id"] or row["user_id"]
                    friend_ids.append(friend_id)
                return friend_ids
        except Exception as e:
            logger.error(f"Failed to get friends: {e}")
            return []

    async def _get_user_status(self, user_id: str) -> Optional[UserStatus]:
        """Get user status from database."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return None

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT user_id, status, last_changed
                    FROM user_status
                    WHERE user_id = $1
                """,
                    user_id,
                )

                if row:
                    return UserStatus(
                        user_id=row["user_id"],
                        status=StatusType(row["status"]),
                        last_changed=row["last_changed"].timestamp(),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user status: {e}")
            return None

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current status."""
        presence_data = self.presence_data.get(user_id, {})
        return {
            "status": presence_data.get("status", StatusType.OFFLINE.value),
            "last_seen": presence_data.get("last_seen", 0),
        }

    def set_user_status(self, user_id: str, status: str) -> bool:
        """Set user's status."""
        if user_id not in self.presence_data:
            return False

        try:
            status_type = StatusType(status)
            self.presence_data[user_id].update(
                {"status": status_type.value,
                 "last_seen": datetime.now().timestamp()}
            )
            logger.info(f"User {user_id} status set to {status}")
            return True
        except ValueError:
            logger.error(f"Invalid status: {status}")
            return False
