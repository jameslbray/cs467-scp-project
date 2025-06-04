"""
RabbitMQ client for notification service.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Callable

from services.rabbitmq.core.client import RabbitMQClient as BaseRabbitMQClient
from services.shared.utils.retry import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)

CHAT_NOTIFICATIONS_QUEUE = "chat_notifications"
NOTIFICATIONS_QUEUE = "notifications"
CONNECTIONS_QUEUE = "connections"


class NotificationRabbitMQClient:
    """RabbitMQ client for notification service."""

    def __init__(self):
        """Initialize the RabbitMQ client."""
        self.rabbitmq = BaseRabbitMQClient()

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            "rabbitmq", failure_threshold=3, reset_timeout=30.0
        )
        self._initialized = False

    # Add in the initialize method or create one if it doesn't exist
    async def initialize(self) -> bool:
        """Initialize the connection manager."""
        if self._initialized:
            logger.warning("Connection manager already initialized")
            return True

        try:
            # Initialize RabbitMQ client with retries
            await with_retry(
                self._initialize_rabbitmq,
                max_attempts=5,
                initial_delay=5.0,
                max_delay=60.0,
                circuit_breaker=self.circuit_breaker,
            )

            self._initialized = True
            logger.info("Connection manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize connection manager: {e}")
            return False

    async def _initialize_rabbitmq(self) -> bool:
        """Initialize RabbitMQ connection and exchanges."""
        # Connect to RabbitMQ
        connected = await self.rabbitmq.connect()
        if not connected:
            raise Exception("Failed to connect to RabbitMQ")

        await self._connect()

        logger.info("RabbitMQ connection and exchanges initialized")
        return True

    async def shutdown(self) -> None:
        """Shutdown the RabbitMQ client."""
        try:
            await self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
        finally:
            self._initialized = False

    async def _connect(self) -> None:
        """Connect to RabbitMQ and set up exchanges and queues."""
        try:
            # Connect to RabbitMQ
            connected = await self.rabbitmq.connect()
            if not connected:
                raise Exception("Failed to connect to RabbitMQ")

            # Bind chat_notifications queue to chat exchange with 'messages' routing key
            await self.rabbitmq.declare_queue(CHAT_NOTIFICATIONS_QUEUE)

            await self.rabbitmq.bind_queue(
                CHAT_NOTIFICATIONS_QUEUE, "chat", "messages"
            )

            logger.info("Connected to RabbitMQ for chat notification events")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def register_chat_consumer(self, chat_handler: Callable) -> None:
        """Register consumer handler for chat messages queue."""
        try:
            if not self._initialized:
                await self.initialize()
            await self.rabbitmq.consume(CHAT_NOTIFICATIONS_QUEUE, chat_handler)
            logger.info("Chat consumer handler registered successfully")
        except Exception as e:
            logger.error(f"Failed to register chat consumer handler: {e}")
            raise

    async def register_notification_consumer(
        self, notification_handler: Callable
    ) -> None:
        """Register consumer handler for general notifications queue."""
        try:
            if not self._initialized:
                await self.initialize()
            await self.rabbitmq.consume(
                NOTIFICATIONS_QUEUE, notification_handler
            )
            logger.info(
                "Notification consumer handler registered successfully"
            )
        except Exception as e:
            logger.error(
                f"Failed to register notification consumer handler: {e}"
            )
            raise

    async def register_connection_consumer(
        self, connection_handler: Callable
    ) -> None:
        """Register consumer handler for connection notifications queue."""
        try:
            if not self._initialized:
                await self.initialize()
            await self.rabbitmq.consume(CONNECTIONS_QUEUE, connection_handler)
            logger.info("Connection consumer handler registered successfully")
        except Exception as e:
            logger.error(
                f"Failed to register connection consumer handler: {e}"
            )
            raise

    async def publish_notification(self, notification: dict) -> bool:
        """Publish a notification event to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()

            def serialize_uuids(obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                raise TypeError(f"Type {type(obj)} not serializable")

            # Create the notification payload
            message = json.dumps(notification, default=serialize_uuids)
            recipient_id = notification.get("recipient_id", [])

            await self.rabbitmq.publish_message(
                exchange="notifications",
                routing_key=f"user.{recipient_id}",
                message=message,
            )
            logger.info(f"Published notification for recipient {recipient_id}")

            return True
        except Exception as e:
            logger.error(f"Failed to publish notification: {e}")
            return False

    async def publish_friend_request(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
        sender_name: str,
    ) -> bool:
        """Publish a friend request notification event to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()

            # Create the notification payload
            message = json.dumps(
                {
                    "source": "notifications",
                    "event_type": "friend_request",
                    "recipient_id": recipient_id,
                    "sender_id": sender_id,
                    "reference_id": str(connection_id),
                    "content_preview": f"{sender_name} sent you a friend request",
                    "timestamp": datetime.now().isoformat(),
                    "read": False,
                    "notification_type": "friend_request",
                }
            )

            await self.rabbitmq.publish_message(
                exchange="notifications",
                routing_key=f"user.{recipient_id}",
                message=message,
            )

            logger.info(
                f"Published friend request notification for recipient {recipient_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request notification: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and self.rabbitmq.is_connected()
