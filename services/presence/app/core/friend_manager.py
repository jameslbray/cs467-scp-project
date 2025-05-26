import logging
from typing import Dict, List, Any
from datetime import datetime
import asyncpg  # type: ignore
from services.shared.utils.retry import CircuitBreaker, with_retry
from services.socket_io.app.core.socket_server import SocketServer
from services.socket_io.app.core.event_schema import EventType, create_event
from services.presence.app.core.presence_manager import PresenceManager
from services.presence.app.core.config import get_db_config

logger = logging.getLogger(__name__)


class FriendManager:
    """
    Manages friend relationships and presence notifications between friends.
    """

    def __init__(
        self,
        socket_server: SocketServer,
        presence_manager: PresenceManager,
    ):
        """
        Initialize the Friend Manager.

        Args:
            socket_server: SocketServer instance for event handling
            presence_manager: PresenceManager instance for status queries
        """
        self.socket_server = socket_server
        self.presence_manager = presence_manager
        self.db_config = get_db_config()
        self.db_pool = None
        self._initialized = False

        # Initialize circuit breakers
        self.db_cb = CircuitBreaker(
            "friend_manager_db",
            failure_threshold=3,
            reset_timeout=30.0
        )
        self.socket_cb = CircuitBreaker(
            "socket_io",
            failure_threshold=3,
            reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the friend manager."""
        if self._initialized:
            return

        try:
            # Initialize database connection with circuit breaker
            await with_retry(
                self._connect_database,
                max_attempts=5,
                initial_delay=5.0,
                max_delay=60.0,
                circuit_breaker=self.db_cb
            )

            self._initialized = True
            logger.info("Friend manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize friend manager: {e}")
            raise

    async def _connect_database(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            self.db_pool = await asyncpg.create_pool(
                min_size=2,
                max_size=10,
                **self.db_config
            )
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if not self._initialized:
            return

        if self.db_pool:
            await self.db_pool.close()

        self._initialized = False
        logger.info("Friend manager closed")

    async def _handle_presence_query(self, event: Dict[str, Any]) -> None:
        """Handle presence query event."""
        user_id = event.get("user_id")
        query_user_id = event.get("query_user_id")

        if not user_id or not query_user_id:
            logger.warning("Missing user_id or query_user_id in query event")
            return

        try:
            # Check if users are friends with circuit breaker
            are_friends = await with_retry(
                lambda: self._check_friendship(user_id, query_user_id),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            if not are_friends:
                logger.warning(
                    f"User {user_id} not authorized to query "
                    f"{query_user_id}'s status"
                )
                return

            # Get status and emit to user with circuit breaker
            status_data = self.presence_manager.get_user_status(query_user_id)
            await with_retry(
                lambda: self.socket_server.emit_to_user(
                    user_id,
                    EventType.PRESENCE_UPDATE,
                    dict(create_event(
                        EventType.PRESENCE_UPDATE,
                        "presence_service",
                        user_id=query_user_id,
                        status=status_data.get("status", "unknown"),
                        last_seen=status_data.get("last_seen", 0)
                    ))
                ),
                max_attempts=3,
                circuit_breaker=self.socket_cb
            )

            logger.info(
                f"User {user_id} queried status of user {query_user_id}")
        except Exception as e:
            logger.error(f"Error handling presence query: {e}")

    async def notify_presence_change(self, user_id: str, status: str) -> None:
        """Notify friends about a user's presence change."""
        try:
            # Get friend IDs with circuit breaker
            friend_ids = await with_retry(
                lambda: self._get_friend_ids(user_id),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            presence_data = self.presence_manager.get_user_status(user_id)
            last_seen = presence_data.get(
                "last_seen", datetime.now().timestamp())

            # Create presence update event
            event_data = create_event(
                EventType.PRESENCE_UPDATE,
                "presence_service",
                user_id=user_id,
                status=status,
                last_seen=last_seen
            )

            # Notify each friend with circuit breaker
            for friend_id in friend_ids:
                await with_retry(
                    lambda: self.socket_server.emit_to_user(
                        friend_id,
                        EventType.PRESENCE_UPDATE,
                        dict(event_data)
                    ),
                    max_attempts=3,
                    circuit_breaker=self.socket_cb
                )

            logger.debug(
                f"Notified {len(friend_ids)} friends about "
                f"{user_id}'s {status} status"
            )
        except Exception as e:
            logger.error(f"Error notifying presence change: {e}")

    async def send_friend_statuses(self, user_id: str, sid: str) -> None:
        """Send friend statuses to a user."""
        try:
            # Get friend IDs with circuit breaker
            friend_ids = await with_retry(
                lambda: self._get_friend_ids(user_id),
                max_attempts=3,
                circuit_breaker=self.db_cb
            )

            # Send status for each friend
            for friend_id in friend_ids:
                status_data = self.presence_manager.get_user_status(friend_id)
                event_data = create_event(
                    EventType.PRESENCE_UPDATE,
                    "presence_service",
                    user_id=friend_id,
                    status=status_data.get("status", "unknown"),
                    last_seen=status_data.get("last_seen", 0)
                )

                # Emit to client with circuit breaker
                await with_retry(
                    lambda: self.socket_server.emit_to_user(
                        user_id,
                        EventType.PRESENCE_UPDATE,
                        dict(event_data)
                    ),
                    max_attempts=3,
                    circuit_breaker=self.socket_cb
                )

            logger.debug(
                f"Sent {len(friend_ids)} friend statuses to user {user_id}"
            )
        except Exception as e:
            logger.error(f"Error sending friend statuses: {e}")

    async def _get_friend_ids(self, user_id: str) -> List[str]:
        """Get a user's friend IDs."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return []

        try:
            async with self.db_pool.acquire() as conn:
                # Query for accepted connections in both directions
                query = """
                    SELECT connected_user_id FROM presence.connections
                    WHERE user_id = $1 AND connection_status = 'accepted'
                    UNION
                    SELECT user_id FROM presence.connections
                    WHERE connected_user_id = $1
                    AND connection_status = 'accepted'
                """
                rows = await conn.fetch(query, user_id)
                return [row["connected_user_id"] or row["user_id"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get friend IDs: {e}")
            return []

    async def _check_friendship(self, user_id: str, friend_id: str) -> bool:
        """Check if two users are friends."""
        if not self.db_pool:
            logger.warning("Database pool not available")
            return False

        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT EXISTS (
                        SELECT 1 FROM presence.connections
                        WHERE (user_id = $1 AND connected_user_id = $2
                            OR user_id = $2 AND connected_user_id = $1)
                        AND connection_status = 'accepted'
                    ) as are_friends
                """
                result = await conn.fetchval(query, user_id, friend_id)
                return bool(result)
        except Exception as e:
            logger.error(f"Failed to check friendship: {e}")
            return False
