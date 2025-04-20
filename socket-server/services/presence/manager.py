import json

import aio_pika
import logging

from .models import UserStatus, StatusType
from .repository import StatusRepository
from .websocket import SocketManager
from .events import ClientEvents, ServerEvents


class PresenceManager:
    """Main service class for managing user presence"""

    def __init__(self, socket_manager: SocketManager, config: dict):
        """Initialize with socket manager and configuration"""
        self.logger = logging.getLogger(__name__)
        self.socket_manager = socket_manager
        self.config = config
        self.repository = StatusRepository(config)
        self.rabbit_connection = None
        self.rabbit_channel = None
        self.rabbit_exchange = None

    async def initialize(self) -> "PresenceManager":
        """Initialize the presence manager"""
        # Initialize repository
        await self.repository.initialize()

        # Connect to RabbitMQ
        self.rabbit_connection = await aio_pika.connect_robust(
            self.config["rabbitmq"]["url"]
        )

        self.rabbit_channel = await self.rabbit_connection.channel()

        # Declare exchanges and queues
        self.rabbit_exchange = await self.rabbit_channel.declare_exchange(
            "user_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        queue = await self.rabbit_channel.declare_queue(
            "presence_updates",
            durable=True
        )

        await queue.bind(self.rabbit_exchange, "status.#")

        # Setup consumer for external status updates
        await queue.consume(self.handle_rabbit_message)

        # Register socket event handlers
        self.socket_manager.register_handlers({
            ClientEvents.UPDATE_STATUS.value: self.handle_status_update,
            ClientEvents.REQUEST_FRIEND_STATUSES.value:
                self.handle_friend_statuses_request
        })

        self.logger.info("Presence manager initialized")
        return self

    async def handle_rabbit_message(self, message: aio_pika.IncomingMessage):
        """Handle messages from RabbitMQ"""
        async with message.process():
            try:
                content = json.loads(message.body.decode())
                await self.handle_external_status_update(content)
            except Exception as e:
                self.logger.error(f"Error processing RabbitMQ message: {e}")

    async def handle_external_status_update(self, status_data: dict):
        """Handle status updates from other services via RabbitMQ"""
        user_status = UserStatus(
            user_id=status_data["user_id"],
            status=status_data["status"],
            last_changed=status_data["last_changed"]
        )

        # Broadcast to relevant clients
        await self.broadcast_status_update(user_status)

    async def handle_connect(self, sid: str, auth_data: dict) -> None:
        """Handle new authenticated connection"""
        user_id = self.authenticate_connection(auth_data)
        if not user_id:
            # Authentication failed
            return

        # Register the connection
        is_first_connection = self.socket_manager.register_user_connection(
            user_id, sid)

        if is_first_connection:
            # User just came online
            await self.update_user_status(user_id, StatusType.ONLINE)

    async def handle_status_update(self, sid: str, data: dict) -> None:
        """Handle status update request from client"""
        user_id = await self.get_user_id_from_sid(sid)
        if not user_id:
            return

        try:
            new_status = StatusType(data["status"])
            user_status = await self.update_user_status(user_id, new_status)

            # Confirm to the user
            await self.socket_manager.emit_to_user(
                user_id,
                ServerEvents.STATUS_UPDATED,
                user_status.dict()
            )
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            await self.socket_manager.sio.emit(
                ServerEvents.ERROR.value,
                {"message": "Failed to update status"},
                room=sid
            )

    async def handle_friend_statuses_request(self, sid: str,
                                             data: dict) -> None:
        """Handle request for friend statuses"""
        user_id = await self.get_user_id_from_sid(sid)
        if not user_id:
            return

        try:
            friend_ids = await self.get_connections(user_id)
            statuses = await self.repository.get_bulk_user_statuses(friend_ids)

            # Send statuses to requester
            await self.socket_manager.sio.emit(
                ServerEvents.FRIEND_STATUSES.value,
                {
                    "statuses": {
                        user_id: status.dict()
                        for user_id, status in statuses.items()
                    }
                },
                room=sid
            )
        except Exception as e:
            self.logger.error(f"Error fetching friend statuses: {e}")
            await self.socket_manager.sio.emit(
                ServerEvents.ERROR.value,
                {"message": "Failed to fetch friend statuses"},
                room=sid
            )

    async def handle_disconnect(self, sid: str) -> None:
        """Handle socket disconnection"""
        user_id = await self.socket_manager.handle_disconnect(sid)
        if user_id:
            # This was the user's last connection, mark them offline
            await self.update_user_status(user_id, StatusType.OFFLINE)

    def authenticate_connection(self, auth_data: dict) -> str | None:
        """Authenticate connection and return user ID if valid"""
        # This would verify JWT token in auth_data
        # Simplified example:
        return auth_data.get("userId")

    async def get_user_id_from_sid(self, sid: str) -> str | None:
        """Find user ID associated with a socket ID"""
        for user_id, sockets in self.socket_manager.connected_users.items():
            if sid in sockets:
                return user_id
        return None

    async def update_user_status(self, user_id: str,
                                 status: StatusType) -> UserStatus:
        """Update a user's status"""
        # Create or update user status
        user_status = UserStatus(user_id=user_id, status=status)

        # Save to repository
        await self.repository.update_user_status(user_status)

        # Publish to RabbitMQ for other services
        await self.rabbit_exchange.publish(
            aio_pika.Message(
                body=json.dumps(user_status.dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=f"status.{status.value}"
        )

        # Broadcast to relevant clients
        await self.broadcast_status_update(user_status)

        return user_status

    async def broadcast_status_update(self, user_status: UserStatus) -> None:
        """Broadcast status update to relevant clients"""
        # Get connections who should receive the update
        connections = await self.get_connections(user_status.user_id)

        # Send to all connected friends
        await self.socket_manager.emit_to_users(
            connections,
            ServerEvents.FRIEND_STATUS_CHANGED,
            user_status.dict()
        )

    async def get_connections(self, user_id: str) -> list[str]:
        """Get users who should receive status updates for this user"""
        # Query connections/friends table
        rows = await self.repository.pg_pool.fetch(
            """
            SELECT connected_user_id FROM connections
            WHERE user_id = $1 AND connection_status = 'accepted'
            UNION
            SELECT user_id FROM connections
            WHERE connected_user_id = $1 AND connection_status = 'accepted'
            """,
            user_id
        )

        return [row["connected_user_id"] or row["user_id"] for row in rows]

    async def get_user_status(self, user_id: str) -> UserStatus | None:
        """Get status for a specific user"""
        return await self.repository.get_user_status(user_id)

    async def close(self) -> None:
        """Cleanup resources"""
        if self.rabbit_channel:
            await self.rabbit_channel.close()

        if self.rabbit_connection:
            await self.rabbit_connection.close()

        await self.repository.close()
        self.logger.info("Presence manager closed")

    def send_friend_statuses(self, sid: str, statuses: dict) -> None:
        """Send friend statuses to a specific socket"""
        self.socket_manager.sio.emit(
            ServerEvents.FRIEND_STATUSES.value,
            {"statuses": statuses},
            room=sid
        )
        self.logger.info(f"Sent friend statuses to {sid}: {statuses}")
