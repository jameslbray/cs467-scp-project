"""
Notification manager for handling user Connection state.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

import asyncpg  # type: ignore
from pydantic.json import pydantic_encoder

from services.shared.utils.retry import CircuitBreaker, with_retry

# from ..db.models import Connection
from ..db.schemas import (
    Connection,
    ConnectionCreate,
    ConnectionStatus,
    ConnectionUpdate,
)
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
            logger.info(f"Searching for connections of user_id: {user_id}")

            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")

                # Only get one direction of each relationship to avoid duplicates
                query = """
                    SELECT
                        c.id,
                        -- If the current user is user_id, then friend_id is their friend
                        -- Otherwise, user_id is their friend
                        CASE WHEN c.user_id = $1 THEN c.friend_id ELSE c.user_id END AS other_user_id,
                        c.user_id,
                        c.friend_id,
                        c.status,
                        c.created_at,
                        c.updated_at
                    FROM connections.connections c
                    WHERE
                        (c.user_id = $1 OR c.friend_id = $1)
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

                logger.info(
                    f"Found {len(connections)} connections for user {user_id}, {connections}"
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
        """Create a new connection (single direction, pending)."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.info(
                f"Creating connection: {connection.user_id} -> {connection.friend_id}"
            )
            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")

                query = """
                    INSERT INTO connections.connections (user_id, friend_id, status)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, friend_id)
                    DO UPDATE SET status = $3, updated_at = NOW()
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                result = await conn.fetchrow(
                    query,
                    connection.user_id,
                    connection.friend_id,
                    connection.status,
                )

                if result:
                    logger.info(f"Connection created with ID: {result['id']}")
                    return Connection(
                        id=result["id"],
                        user_id=result["user_id"],
                        friend_id=result["friend_id"],
                        status=result["status"],
                        created_at=result["created_at"],
                        updated_at=result["updated_at"],
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
        """Update an existing connection. If accepting, create reverse direction if not exists. If rejecting, only update the original direction."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:
            logger.debug(f"Updating connection for {connection.user_id}")
            async with self.postgres_client.acquire() as conn:
                await conn.execute("SET search_path TO connections, public")

                query = """
                    UPDATE connections.connections
                    SET status = $1, updated_at = NOW()
                    WHERE (user_id = $2 AND friend_id = $3)
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                result = await conn.fetchrow(
                    query,
                    connection.status,
                    connection.user_id,
                    connection.friend_id,
                )

                if not result:
                    logger.error("Failed to update connection")
                    return None

                # If status is ACCEPTED, create reverse direction if not exists
                if connection.status == ConnectionStatus.ACCEPTED:
                    reverse_query = """
                        INSERT INTO connections.connections (user_id, friend_id, status)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, friend_id) DO NOTHING
                        RETURNING id, user_id, friend_id, status, created_at, updated_at
                    """
                    reverse_result = await conn.fetchrow(
                        reverse_query,
                        connection.friend_id,
                        connection.user_id,
                        ConnectionStatus.ACCEPTED,
                    )
                    if reverse_result:
                        logger.info(
                            f"Reverse connection created: {reverse_result['id']}"
                        )
                # If status is REJECTED, do nothing else (no reverse direction)

                logger.info(f"Connection updated with ID: {result['id']}")
                return Connection(
                    id=result["id"],
                    user_id=result["user_id"],
                    friend_id=result["friend_id"],
                    status=result["status"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )

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
                event_type = "friend_request"
            elif notification_type == "friend_accepted":
                event_type = "friend_accepted"
            else:
                event_type = notification_type

            if not correlation_id:
                import uuid

                correlation_id = str(uuid.uuid4())

            routing_key = f"user.{recipient_id}"

            # Prepare message
            message = json.dumps(
                {
                    "source": "connections",
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
            if notification_type == "friend_request":
                await self.rabbitmq.publish_friend_request(  # Use specific method for requests
                    message=message,
                    routing_key=routing_key,
                    reply_to=reply_to or "connection_notifications",
                )
            else:  # For friend_accepted and other types
                await self.rabbitmq.publish_friend_accepted(
                    exchange="connections",
                    message=message,
                    routing_key=routing_key,
                )

            logger.info(
                f"Published {notification_type} notification for recipient {recipient_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish notification event: {e}")
            return False

    async def _process_connection_message(self, message) -> None:
        logger.info(f"[CONSUMER] Received message: {message!r}")
        try:
            logger.info(f"[CONSUMER] Message body: {message.body!r}")
            logger.info(
                f"[CONSUMER] Message properties: correlation_id={message.correlation_id}, reply_to={message.reply_to}"
            )
            body = json.loads(message.body.decode())

            if "source" in body and body["source"] == "connections":
                logger.warning("[CONSUMER] Invalid message source, ignoring")
                await message.ack()
                logger.info("[CONSUMER] Message acked (invalid source)")
                return

            logger.info(f"[CONSUMER] Processing connection message: {body}")

            if "event_type" not in body:
                logger.error("[CONSUMER] Missing event_type in message")
                await message.nack(requeue=False)
                logger.info("[CONSUMER] Message nacked (missing event_type)")
                return
            event_type = body["event_type"]
            logger.info(f"[CONSUMER] Event type: {event_type}")

            if event_type == "connection:friend_request":
                recipient_id = body.get("recipient_id")
                sender_id = body.get("sender_id")
                reference_id = body.get("reference_id")
                content_preview = body.get("content_preview", "")

                if not recipient_id or not sender_id or not reference_id:
                    logger.error("Missing required fields for friend request")
                    await message.nack(requeue=False)
                    return

                # Add friend request to database
                created_connection = await self.create_connection(
                    ConnectionCreate(
                        user_id=sender_id,
                        friend_id=recipient_id,
                        status=ConnectionStatus.PENDING,
                    )
                )
                logger.info(f"Created connection: {created_connection}")

                if not created_connection:
                    logger.error(
                        f"Failed to create connection for {recipient_id} -> {sender_id}"
                    )
                    await message.nack(requeue=False)
                    return

                # Publish friend request notification
                await self.publish_notification_event(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    reference_id=reference_id,
                    notification_type="friend_request",
                    content_preview=content_preview,
                )
                logger.info(
                    "[CONSUMER] Finished processing friend_request event"
                )
            elif event_type == "connection:friend_accepted":
                recipient_id = body.get("recipient_id")
                sender_id = body.get("sender_id")
                reference_id = body.get("reference_id")
                content_preview = body.get("content_preview", "")

                if not recipient_id or not sender_id or not reference_id:
                    logger.error("Missing required fields for friend accepted")
                    await message.nack(requeue=False)
                    return

                # Update connection status to accepted
                updated_connection = await self.update_connection(
                    ConnectionUpdate(
                        id=body.get("id"),
                        user_id=sender_id,
                        friend_id=recipient_id,
                        status=ConnectionStatus.ACCEPTED,
                        updated_at=datetime.now(),
                        created_at=body.get("created_at", datetime.now()),
                    )
                )
                if not updated_connection:
                    logger.error(
                        f"Failed to update connection for {recipient_id} -> {sender_id}"
                    )
                    await message.nack(requeue=False)
                    return

                # Publish friend accepted notification
                await self.publish_notification_event(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    reference_id=reference_id,
                    notification_type="friend_accepted",
                    content_preview=content_preview,
                )
                logger.info(
                    "[CONSUMER] Finished processing friend_accepted event"
                )
            elif event_type == "connections:get_friends":
                user_id = body.get("user_id")
                logger.info(f"[CONSUMER] get_friends for user_id: {user_id}")

                if not user_id:
                    logger.error(
                        "[CONSUMER] Missing user_id for get_friends event"
                    )
                    await message.nack(requeue=False)
                    logger.info("[CONSUMER] Message nacked (missing user_id)")
                    return

                # Fetch user's connections
                connections = await self.get_user_connections(user_id)
                logger.info(f"[CONSUMER] Connections fetched: {connections}")
                if connections is None:
                    logger.error(
                        f"[CONSUMER] Failed to fetch connections for user {user_id}"
                    )
                    await message.nack(requeue=False)
                    logger.info(
                        "[CONSUMER] Message nacked (failed to fetch connections)"
                    )
                    return

                # Filter connections to only include accepted friends
                connections = [
                    conn
                    for conn in connections
                    if conn.status == ConnectionStatus.ACCEPTED
                ]
                logger.info(
                    f"[CONSUMER] Filtered accepted connections: {connections}"
                )

                # Publish the connections back to the requester
                response_message = json.dumps(
                    {
                        "source": "connections",
                        "event_type": "friends_list",
                        "user_id": user_id,
                        "friends": connections,
                    },
                    default=pydantic_encoder,
                )
                logger.info(f"[CONSUMER] Response message: {response_message}")
                logger.info(
                    f"[CONSUMER] Publishing to reply_to={message.reply_to}, correlation_id={message.correlation_id}"
                )

                await self.rabbitmq.publish_friends_list(
                    reply_to=message.reply_to,
                    message=response_message,
                    correlation_id=message.correlation_id,
                )
                logger.info("[CONSUMER] Finished processing get_friends event")
            else:
                logger.error(f"[CONSUMER] Unknown event type: {event_type}")
                await message.nack(requeue=False)
                logger.info("[CONSUMER] Message nacked (unknown event type)")
                return

            await message.ack()
            logger.info("[CONSUMER] Message acked (success)")

        except Exception as e:
            logger.error(f"[CONSUMER] Error processing connection update: {e}")
            await message.nack(requeue=False)
            logger.info("[CONSUMER] Message nacked (exception)")
