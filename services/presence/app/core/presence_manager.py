import logging
from typing import Dict, List, Any
from datetime import datetime

from services.socket_io.app.core.service_connector import ServiceConnector
from services.socket_io.app.core.event_schema import EventType

logger = logging.getLogger(__name__)


class PresenceManager:
    """
    Manages user presence state and status updates.
    """

    def __init__(
        self,
        socket_connector: ServiceConnector,
        config: Dict[str, Any]
    ):
        """
        Initialize the Presence Manager.

        Args:
            socket_connector: ServiceConnector for event handling
            config: Service configuration
        """
        self.socket_connector = socket_connector
        self.config = config
        self.presence_data: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the presence manager."""
        if self._initialized:
            return

        self.socket_connector.on_event(
            EventType.USER_CONNECTED,
            self._handle_user_connected
        )
        self.socket_connector.on_event(
            EventType.USER_DISCONNECTED,
            self._handle_user_disconnected
        )
        self.socket_connector.on_event(
            EventType.PRESENCE_UPDATE,
            self._handle_presence_update
        )

        self._initialized = True
        logger.info("Presence manager initialized")

    async def close(self) -> None:
        """Clean up resources."""
        if not self._initialized:
            return

        self.socket_connector.off_event(
            EventType.USER_CONNECTED,
            self._handle_user_connected
        )
        self.socket_connector.off_event(
            EventType.USER_DISCONNECTED,
            self._handle_user_disconnected
        )
        self.socket_connector.off_event(
            EventType.PRESENCE_UPDATE,
            self._handle_presence_update
        )

        self._initialized = False
        logger.info("Presence manager closed")

    async def _handle_user_connected(
        self,
        event: Dict[str, Any]
    ) -> None:
        """Handle user connected event."""
        user_id = event.get("user_id")
        sid = event.get("sid")

        if not user_id or not sid:
            logger.warning("Missing user_id or sid in connect event")
            return

        self.socket_connector.register_user(sid, user_id)
        self.presence_data[user_id] = {
            "status": "online",
            "last_seen": datetime.now().timestamp(),
            "sid": sid
        }

        logger.info(f"User {user_id} connected with socket {sid}")

    async def _handle_user_disconnected(
        self,
        event: Dict[str, Any]
    ) -> None:
        """Handle user disconnected event."""
        user_id = event.get("user_id")
        sid = event.get("sid")

        if not user_id or not sid:
            logger.warning("Missing user_id or sid in disconnect event")
            return

        self.socket_connector.unregister_user(sid)
        if user_id in self.presence_data:
            self.presence_data[user_id].update({
                "status": "offline",
                "last_seen": datetime.now().timestamp(),
                "sid": None
            })

        logger.info(f"User {user_id} disconnected from socket {sid}")

    async def _handle_presence_update(
        self,
        event: Dict[str, Any]
    ) -> None:
        """Handle presence update event."""
        user_id = event.get("user_id")
        status = event.get("status")

        if not user_id or not status:
            logger.warning("Missing user_id or status in update event")
            return

        if user_id in self.presence_data:
            self.presence_data[user_id].update({
                "status": status,
                "last_seen": datetime.now().timestamp()
            })

        logger.info(f"User {user_id} status updated to {status}")

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current status."""
        presence_data = self.presence_data.get(user_id, {})
        return {
            "status": presence_data.get("status", "offline"),
            "last_seen": presence_data.get("last_seen", 0)
        }

    def set_user_status(
        self,
        user_id: str,
        status: str
    ) -> bool:
        """Set user's status."""
        if user_id not in self.presence_data:
            return False

        self.presence_data[user_id].update({
            "status": status,
            "last_seen": datetime.now().timestamp()
        })

        logger.info(f"User {user_id} status set to {status}")
        return True
