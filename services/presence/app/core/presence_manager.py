"""
Presence manager for handling user presence state.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from datetime import datetime
import asyncpg  # type: ignore
from enum import Enum
from uuid import UUID
from services.shared.utils.retry import CircuitBreaker, with_retry
from .presence_rabbitmq import PresenceRabbitMQClient

# configure logging
logger = logging.getLogger(__name__)


class StatusType(str, Enum):
    """User status types."""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


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
        rabbitmq_client: PresenceRabbitMQClient
    ):
        """Initialize the presence manager.

        Args:
            config: Configuration dictionary containing RabbitMQ settings
            rabbitmq_client: RabbitMQ client instance from app.state
        """
        self.config = config
        self._initialized = False
        self.db_pool: Optional[asyncpg.Pool] = None
        self.rabbitmq = rabbitmq_client
        
        self.db_cb = CircuitBreaker(
            "postgres",
            failure_threshold=3,
            reset_timeout=30.0
        )
        
        self.rabbitmq_cb = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the presence manager."""
        if self._initialized:
            logger.warning("Presence manager already initialized")
            return

        try:
            # Initialize database if this is the presence service
            if "postgres" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb
                )

            # Register message handlers with RabbitMQ client
            await self.rabbitmq.register_consumers(
                self._process_presence_message,
                # Could be used for new users
                self._process_user_events_message
            )

            self._initialized = True
            logger.info("Presence manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize presence manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the presence manager."""
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

    async def check_connection_health(self):
        """Check if the database connection is online."""
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
            
            logger.info(f"Processing presence message: {message_type}")

            if message_type == "presence:status:update":
                await self._handle_status_update(body, message)
            elif message_type == "presence:status:query":
                await self._handle_status_query(body, message)
            else:
                # Handle friend statuses request (from socket server)
                user_id = body.get("user_id")
                if user_id:
                    await self._handle_friend_statuses_request(body, message)
                else:
                    logger.warning(f"Unknown presence message type: {message_type}")
                    await message.ack()

        except Exception as e:
            logger.error(f"Error processing presence message: {e}")
            await message.nack(requeue=False)

    async def _handle_status_update(self, data: Dict[str, Any], message: Any) -> None:
        """Handle status update messages."""
        # Skip if this message came from ourselves
        if data.get("source") == "presence_service":
            await message.ack()
            return
        
        try:
            user_id = data.get("user_id")
            status = data.get("status")
            last_status_change = data.get("last_status_change")

            if user_id and status:
                if self.db_pool:
                    await with_retry(
                        lambda: self._save_user_status(
                            user_id, StatusType(status), last_status_change),
                        max_attempts=3,
                        circuit_breaker=self.db_cb
                    )

                    # Publish status update to notify friends
                    await with_retry(
                        lambda: self._publish_status_update(
                            user_id,
                            StatusType(status),
                            last_status_change
                        ),
                        max_attempts=3,
                        circuit_breaker=self.rabbitmq_cb
                    )

            await message.ack()
        except Exception as e:
            logger.error(f"Error handling status update: {e}")
            await message.nack(requeue=False)

    async def _handle_status_query(self, data: Dict[str, Any], message: Any) -> None:
        """Handle status query messages."""
        # Skip if this message came from ourselves
        if data.get("source") == "presence_service":
            await message.ack()
            return
        try:
            user_id = data.get("user_id") or data.get("target_user_id")
            correlation_id = message.correlation_id
            
            if user_id:
                status = await with_retry(
                    lambda: self._get_user_status(user_id),
                    max_attempts=3,
                    circuit_breaker=self.db_cb
                )
                
                # Publish status response back
                await self.rabbitmq.publish_status_query_response(
                    user_id,
                    status.status.value if status else StatusType.OFFLINE.value,
                    status.last_status_change if status else datetime.now().timestamp(),
                    correlation_id=correlation_id
                )

            await message.ack()
        except Exception as e:
            logger.error(f"Error handling status query: {e}")
            await message.nack(requeue=False)

    async def _handle_friend_statuses_request(
        self,
        data: Dict[str, Any],
        message: Any
    ) -> None:
        """Handle friend statuses request messages."""
        # Skip if this message came from ourselves
        if data.get("source") == "presence_service":
            await message.ack()
            return
        try:
            properties = message.properties
            correlation_id = properties.correlation_id
            reply_to = properties.reply_to
            
            body = json.loads(message.body.decode())
            user_id = body.get("user_id")
            friend_ids = body.get("friend_ids", [])
            
            if not friend_ids:
                logger.error("No friend_ids in friend statuses request")
                await message.ack()
                return
            
            if not isinstance(friend_ids, list):
                logger.error("friend_ids should be a list")
                await message.ack()
                return
            
            if not user_id:
                logger.error("No user_id in friend statuses request")
                await message.ack()
                return
                
            logger.info(f"Getting friend statuses for user {user_id}")
                        
            # Get status for each friend
            statuses = {}
            for friend_id in friend_ids:
                try:
                    status = await with_retry(
                        lambda: self._get_user_status(friend_id),
                        max_attempts=3,
                        circuit_breaker=self.db_cb
                    )
                    
                    if status:
                        statuses[friend_id] = {
                            "user_id": friend_id,
                            "status": status.status.value,
                            "last_status_change": status.last_status_change
                        }
                    else:
                        statuses[friend_id] = {
                            "user_id": friend_id,
                            "status": StatusType.OFFLINE.value,
                            "last_status_change": datetime.now().timestamp()
                        }
                except Exception as e:
                    logger.error(f"Error getting status for friend {friend_id}: {e}")
                    statuses[friend_id] = {
                        "user_id": friend_id,
                        "status": StatusType.OFFLINE.value,
                        "last_status_change": datetime.now().timestamp()
                    }
            
            await self.rabbitmq.publish_friend_statuses_response(
                user_id,  # requesting_user_id
                statuses,
                correlation_id=correlation_id,
                reply_to=reply_to
            )
            
            logger.info(f"Published friend statuses response for user {user_id}")
            await message.ack()
        except Exception as e:
            logger.error(f"Error handling friend statuses request: {e}")
            await message.nack(requeue=False)

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

            logger.info(f"User {user_id} status updated to {status}")
            return True

        except ValueError:
            logger.error(f"Invalid status: {status}")
            return False

    async def _publish_status_update(
        self,
        user_id: str,
        status: StatusType,
        last_status_change: Optional[float] = None
    ) -> None:
        """Publish status update to RabbitMQ."""
        if not self.rabbitmq:
            logger.warning("No RabbitMQ client available, can't publish status update")
            return
            
        try:
            # Use the publish method
            await self.rabbitmq.publish_status_update(
                user_id,
                status.value,
                last_status_change
            )
            logger.debug(f"Published status update for {user_id}: {status.value}")
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")
            raise

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
            logger.error(f"Invalid UUID format for user_id: {user_id} error: {e}")
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

        # Fetch from database
        user_status = await self._get_user_status(user_id)
        if user_status is None:
            return default_status

        return UserStatus(
            user_id=str(user_status.user_id),  # Convert UUID to string
            status=user_status.status,
            last_status_change=user_status.last_status_change
        ).dict()

    async def set_user_status(self, 
                              user_id: str, 
                              status: str) -> bool:
        """Set user's status."""
        try:
            status_type = StatusType(status)

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
        """Set new user's initial status to online."""
        return await self.set_user_status(user_id, StatusType.ONLINE.value)

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
                    uuid_user_id = (
                        UUID(int=int(user_id))
                        if user_id.isdigit()
                        else UUID(bytes=user_id.encode(), version=4)
                    )
                    logger.debug(
                        (
                            f"Generated UUID v4 from string:"
                            f"{user_id} -> {uuid_user_id}"
                        )
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

    async def _process_user_events_message(self, message: Any) -> None:
        """Process user events messages from RabbitMQ."""
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("type")

            logger.info(f"Processing user event message: {event_type}")

            if event_type == "user:created":
                user_id = body.get("user_id")
                if user_id:
                    await self.set_new_user_status(user_id)
                else:
                    logger.warning("No user_id in user created event")
            else:
                logger.warning(f"Unknown user event type: {event_type}")

            await message.ack()
        except Exception as e:
            logger.error(f"Error processing user events message: {e}")
            await message.nack(requeue=False)
