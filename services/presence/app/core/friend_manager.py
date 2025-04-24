import logging
from typing import Dict, List, Any
from datetime import datetime
from services.presence.app.core.presence_manager import PresenceManager

from services.socket_io.app.core.service_connector import ServiceConnector
from services.socket_io.app.core.event_schema import EventType

logger = logging.getLogger(__name__)


class FriendManager:
    """
    Manages friend relationships and presence notifications between friends.
    """

    def __init__(
        self,
        socket_connector: ServiceConnector,
        presence_manager: 'PresenceManager'
    ):
        """
        Initialize the Friend Manager.

        Args:
            socket_connector: ServiceConnector for event handling
            presence_manager: PresenceManager instance for status queries
        """
        self.socket_connector = socket_connector
        self.presence_manager = presence_manager
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the friend manager."""
        if self._initialized:
            return

        self.socket_connector.on_event(
            EventType.PRESENCE_QUERY,
            self._handle_presence_query
        )

        self._initialized = True
        logger.info("Friend manager initialized")

    async def close(self) -> None:
        """Clean up resources."""
        if not self._initialized:
            return

        self.socket_connector.off_event(
            EventType.PRESENCE_QUERY,
            self._handle_presence_query
        )

        self._initialized = False
        logger.info("Friend manager closed")

    async def _handle_presence_query(
        self,
        event: Dict[str, Any]
    ) -> None:
        """Handle presence query event."""
        user_id = event.get("user_id")
        query_user_id = event.get("query_user_id")

        if not user_id or not query_user_id:
            logger.warning("Missing user_id or query_user_id in query event")
            return

        status_data = self.presence_manager.get_user_status(query_user_id)
        await self.socket_connector.emit_to_user(
            user_id,
            EventType.PRESENCE_UPDATE,
            user_id=query_user_id,
            status=status_data.get("status", "unknown"),
            last_seen=status_data.get("last_seen", 0)
        )

        logger.info(f"User {user_id} queried status of user {query_user_id}")

    async def notify_presence_change(
        self,
        user_id: str,
        status: str
    ) -> None:
        """Notify friends about a user's presence change."""
        friend_ids = await self._get_friend_ids(user_id)
        presence_data = self.presence_manager.get_user_status(user_id)
        last_seen = presence_data.get("last_seen", datetime.now().timestamp())

        for friend_id in friend_ids:
            await self.socket_connector.emit_to_user(
                friend_id,
                EventType.PRESENCE_UPDATE,
                user_id=user_id,
                status=status,
                last_seen=last_seen
            )

        logger.debug(
            f"Notified {len(friend_ids)} friends about "
            f"{user_id}'s {status} status"
        )

    async def send_friend_statuses(
        self,
        user_id: str,
        sid: str
    ) -> None:
        """Send friend statuses to a user."""
        friend_ids = await self._get_friend_ids(user_id)

        for friend_id in friend_ids:
            status_data = self.presence_manager.get_user_status(friend_id)
            await self.socket_connector.emit_to_client(
                sid,
                EventType.PRESENCE_UPDATE,
                user_id=friend_id,
                status=status_data.get("status", "unknown"),
                last_seen=status_data.get("last_seen", 0)
            )

        logger.debug(
            f"Sent {len(friend_ids)} friend statuses to user {user_id}")

    async def _get_friend_ids(self, user_id: str) -> List[str]:
        """Get a user's friend IDs."""
        # TODO: Implement database query to get friend IDs
        return []
