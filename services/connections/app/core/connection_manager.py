"""
Notification manager for handling user Connection state.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

import asyncpg  # type: ignore

from services.shared.utils.retry import CircuitBreaker, with_retry

from ..db.models import Connection
from ..db.schemas import ConnectionCreate, ConnectionUpdate
from .connections_rabbitmq import ConnectionsRabbitMQClient

# configure logging
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages user Connection state."""

    def __init__(
        self,
        config: dict[str, Any],
        rabbitmq_client: ConnectionsRabbitMQClient,
    ):
        """Initialize the notification manager.

        Args:
            config: Configuration dictionary containing RabbitMQ settings
            socket_server: Optional Socket.IO server instance
        """
        self.config = config
        self._initialized = False
        self.postgres_client: asyncpg.Pool

        # Initialize RabbitMQ client
        self.rabbitmq = rabbitmq_client

        self.db_cb = CircuitBreaker(
            "postgres", failure_threshold=3, reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the Connections manager."""
        if self._initialized:
            logger.warning("Connection manager already initialized")
            return

        try:
            # Initialize database connection with circuit breaker
            if "postgres" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb,
                )
            await self.rabbitmq.register_consumers(
                self._process_connection_message
            )
            self._initialized = True
            logger.info("Connection manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Connection manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the Connection manager."""

        try:
            if self.postgres_client:
                await self.postgres_client.close()
                logger.info("Postgres connection closed")
        except Exception as e:
            logger.error(f"Error closing Postgres connection: {e}")
        finally:
            self.postgres_client = None
            logger.info("Connection manager shut down")

    async def _connect_database(self) -> None:
        """Connect to PostgreSQL."""
        config = self.config["postgres"].copy()
        try:
            if "options" in config:
                del config["options"]
            self.postgres_client = await asyncpg.create_pool(
                min_size=2, max_size=10, **config
            )
            logger.info("Connected to PostgreSQL database")
            # Set search path for all connections in the pool
            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")
            logger.info("Postgres search_path set for pool")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def check_connection_health(self):
        try:
            await self.postgres_client.execute("SELECT 1")
            return True
        except Exception:
            logger.error("Postgres connection failed")
            return False

    async def get_user_connections(self, user_id: str) -> List[Connection]:
        """Get a user's connections."""
        # Default values
        empty_connections: List[Connection] = []

        # Fetch from database if not in cache
        user_connections = await self._get_user_connections(user_id)
        if user_connections:
            return user_connections

        return empty_connections

    async def _get_user_connections(
        self, user_id: str
    ) -> list[Connection] | None:
        """Get a user's connections from database."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.debug(f"Searching for connections of user_id: {user_id}")

            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")

                # Only get one direction of each relationship to avoid duplicates
                query = """
                    SELECT DISTINCT ON (LEAST(user_id, friend_id), GREATEST(user_id, friend_id))
                        * FROM connections.connections
                    WHERE (user_id = $1 OR friend_id = $1)
                    ORDER BY LEAST(user_id, friend_id), GREATEST(user_id, friend_id), created_at DESC
                """
                rows = await conn.fetch(query, user_id)

                # Convert rows to list of Connection
                connections = []
                for row in rows:
                    try:
                        # Convert row to dict and handle UUID types
                        connection = Connection(
                            id=row["id"],
                            user_id=row["user_id"],
                            friend_id=row["friend_id"],
                            status=row["status"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )
                        connections.append(connection)
                    except Exception as e:
                        logger.error(
                            f"Error converting row to connection: {e}"
                        )

                return connections

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user connections: {e}")
            return None

    async def get_all_connections(self) -> List[Connection]:
        """Get all connections."""
        # Default values
        empty_connections: List[Connection] = []

        # Fetch from database if not in cache
        user_connections = await self._get_all_connections()
        if user_connections:
            return user_connections

        return empty_connections

    async def _get_all_connections(self) -> list[Connection] | None:
        """Get all user connections from database."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.debug("Searching for all connections")
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection

                await conn.execute("SET search_path TO connections, public")

                query = """
                    SELECT * FROM connections.connections
                """
                # Execute the query
                rows = await conn.fetch(query)

                # Convert rows to list of Connection
                connections = []
                for row in rows:
                    try:
                        # Convert row to dict and handle UUID types
                        connection = Connection(
                            id=row["id"],
                            user_id=row["user_id"],
                            friend_id=row["friend_id"],
                            status=row["status"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )
                        connections.append(connection)
                    except Exception as e:
                        logger.error(
                            f"Error converting row to connection: {e}"
                        )

                return connections

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user connections: {e}")
            return None

    async def create_connection(
        self, connection: ConnectionCreate
    ) -> Connection | None:
        """Create a new connection."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.debug(
                f"Creating connection: {connection.user_id} -> {connection.friend_id}"
            )
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                await conn.execute("SET search_path TO connections, public")

                # First direction (user_id -> friend_id)
                query1 = """
                    INSERT INTO connections.connections (user_id, friend_id, status)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, friend_id)
                    DO UPDATE SET status = $3, updated_at = NOW()
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                # Execute first query
                result1 = await conn.fetchrow(
                    query1,
                    connection.user_id,
                    connection.friend_id,
                    connection.status,
                )

                # Second direction (friend_id -> user_id)
                query2 = """
                    INSERT INTO connections.connections (user_id, friend_id, status)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, friend_id)
                    DO UPDATE SET status = $3, updated_at = NOW()
                    RETURNING id
                """
                # Execute second query
                result2 = await conn.fetchrow(
                    query2,
                    connection.friend_id,
                    connection.user_id,
                    connection.status,
                )

                if result1 and result2:
                    logger.info(
                        f"Bidirectional connection created with ID: {result1['id']}"
                    )
                    return Connection(
                        id=result1["id"],
                        user_id=result1["user_id"],
                        friend_id=result1["friend_id"],
                        status=result1["status"],
                        created_at=result1["created_at"],
                        updated_at=result1["updated_at"],
                    )
                else:
                    logger.error("Failed to create connection")
                    return None

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

    async def update_connection(
        self, connection: ConnectionUpdate
    ) -> Connection | None:
        """Update an existing connection."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.debug(f"Updating connection for {connection.user_id}")
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                await conn.execute("SET search_path TO connections, public")

                query = """
                    UPDATE connections.connections
                    SET status = $1, updated_at = NOW()
                    WHERE (user_id = $2 AND friend_id = $3)
                    OR (user_id = $3 AND friend_id = $2)
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                # Execute the query
                result = await conn.fetchrow(
                    query,
                    connection.status,
                    connection.user_id,
                    connection.friend_id,
                )

                if result:
                    logger.info(
                        f"Connection updated with ID: {connection.user_id}"
                    )
                    return Connection(
                        id=result["id"],
                        user_id=result["user_id"],
                        friend_id=result["friend_id"],
                        status=result["status"],
                        created_at=result["created_at"],
                        updated_at=result["updated_at"],
                    )
                else:
                    logger.error("Failed to update connection")
                    return None

        except Exception as e:
            logger.error(f"Failed to update connection: {e}")
            return None

    async def get_connection(
        self, user_id: str, friend_id: str
    ) -> Connection | None:
        """Get a specific connection between user and friend."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")
                query = """
                    SELECT * FROM connections.connections
                    WHERE (user_id = $1 AND friend_id = $2)
                    OR (user_id = $2 AND friend_id = $1)
                """
                row = await conn.fetchrow(query, user_id, friend_id)

                if row:
                    return Connection(
                        id=row["id"],
                        user_id=row["user_id"],
                        friend_id=row["friend_id"],
                        status=row["status"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            return None

    async def publish_notification_event(
        self,
        recipient_id: str,
        sender_id: str,
        reference_id: str,
        notification_type: str,
        content_preview: str,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """Publish a notification event to RabbitMQ."""
        try:
            # Determine the correct routing key based on notification type
            if notification_type == "friend_request":
                routing_key = "connection.friend_request"
                event_type = "friend_request"
            elif notification_type == "friend_accepted":
                routing_key = "connection.friend_accepted"
                event_type = "friend_accepted"
            else:
                routing_key = f"connection.{notification_type}"
                event_type = notification_type

            if not correlation_id:
                import uuid

                correlation_id = str(uuid.uuid4())

            # Prepare message
            message = json.dumps(
                {
                    "event_type": event_type,
                    "recipient_id": recipient_id,
                    "sender_id": sender_id,
                    "reference_id": str(reference_id),
                    "notification_type": notification_type,
                    "content_preview": content_preview,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Publish friend request event using correct parameters
            await self.rabbitmq.publish_friend_request(
                recipient_id=recipient_id,
                sender_id=sender_id,
                connection_id=correlation_id,
                message=message,
                routing_key=routing_key,
                reply_to=reply_to,
            )

            logger.info(
                f"Published {notification_type} notification for recipient {recipient_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish notification event: {e}")
            return False

    async def _process_connection_message(self, message) -> None:
        """Process a connection update message from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            logger.info(f"Processing connection update: {body}")

            await message.ack()
        except Exception as e:
            logger.error(f"Error processing connection update: {e}")
            await message.nack(requeue=False)
