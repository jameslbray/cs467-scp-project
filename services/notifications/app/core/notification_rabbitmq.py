"""
RabbitMQ client for notification service.
"""
import logging
import json
from typing import Callable
from datetime import datetime
import uuid

from services.rabbitmq.core.client import RabbitMQClient as BaseRabbitMQClient
from services.shared.utils.retry import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)


class NotificationRabbitMQClient:
    """RabbitMQ client for notification service."""

    def __init__(self):
        """Initialize the RabbitMQ client."""
        self.rabbitmq = BaseRabbitMQClient()

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30.0
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

            # Declare exchanges
            await self.rabbitmq.declare_exchange("connections", "topic")
            await self.rabbitmq.declare_exchange("chat", "topic")

            await self.rabbitmq.declare_queue(
                "connections_queue",
                durable=True
            )
            
            await self.rabbitmq.declare_queue(
                "chat_queue",
                durable=True
            )

            # Connection events (friend requests, etc)
            await self.rabbitmq.bind_queue(
                "connections_queue",
                "connections",
                "user.#"  # All connection-related events
            )
            
            # Chat messages
            await self.rabbitmq.bind_queue(
                "chat_queue",
                "chat",
                "chat_notifications.#"  # All chat messages
            )

            logger.info("Connected to RabbitMQ for notification events")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def register_consumers(
        self,
        # notifications_handler: Callable,
        connection_handler: Callable,
        chat_handler: Callable
    ) -> None:
        """Register consumer handlers for different queues."""
        try:
            if not self._initialized:
                await self.initialize()

            await self.rabbitmq.consume(
                "connections_queue",
                connection_handler
            )

            await self.rabbitmq.consume(
                "chat_queue",
                chat_handler
            )

            logger.info("Consumer handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register consumer handlers: {e}")
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
                message=message
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
            message = json.dumps({
                "source": "notifications",
                "event_type": "friend_request",
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(connection_id),
                "content_preview": f"{sender_name} sent you a friend request",
                "timestamp": datetime.now().isoformat(),
                "read": False,
                "notification_type": "friend_request"
            })

            await self.rabbitmq.publish_message(
                exchange="notifications",
                routing_key=f"user.{recipient_id}",
                message=message
            )

            logger.info(f"Published friend request notification for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request notification: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and self.rabbitmq.is_connected()
