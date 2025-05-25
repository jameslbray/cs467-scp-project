"""
RabbitMQ client for notification service.
"""
import logging
import json
from typing import Any, Callable, Dict, Optional
from datetime import datetime
from bson import ObjectId

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

        # Declare exchanges
        await self.rabbitmq.declare_exchange("connection_events", "topic")
        await self.rabbitmq.declare_exchange("notifications", "topic")

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
            await self.rabbitmq.declare_exchange("notification_events", "topic")
            await self.rabbitmq.declare_exchange("connection_events", "topic")
            await self.rabbitmq.declare_exchange("message_events", "topic")

            # Declare queues for different types of notifications
            await self.rabbitmq.declare_queue(
                "general_notifications",
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "user_notifications",
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "connection_notifications",
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "message_notifications",
                durable=True
            )

            # Bind queues to exchanges with routing keys
            # General notifications for all users
            await self.rabbitmq.bind_queue(
                "general_notifications",
                "notification_events",
                "broadcast.#"  # All broadcast messages
            )

            # User-specific notifications
            await self.rabbitmq.bind_queue(
                "user_notifications",
                "notification_events",
                "user.#"  # All user-targeted notifications
            )

            # Connection events (friend requests, etc)
            await self.rabbitmq.bind_queue(
                "connection_notifications",
                "connection_events",
                "connection.#"  # All connection-related events
            )

            # Message events (new messages, etc)
            await self.rabbitmq.bind_queue(
                "message_notifications",
                "message_events",
                "message.#"  # All message-related events
            )

            logger.info("Connected to RabbitMQ for notification events")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def register_consumers(
        self, 
        general_handler: Callable, 
        user_handler: Callable,
        connection_handler: Callable,
        message_handler: Callable
    ) -> None:
        """Register consumer handlers for different queues."""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Start consuming messages with provided handlers
            await self.rabbitmq.consume(
                "general_notifications",
                general_handler
            )
            await self.rabbitmq.consume(
                "user_notifications",
                user_handler
            )
            await self.rabbitmq.consume(
                "connection_notifications",
                connection_handler
            )
            await self.rabbitmq.consume(
                "message_notifications",
                message_handler
            )
            
            logger.info("Consumer handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register consumer handlers: {e}")
            raise

    async def publish_notification(
        self,
        recipient_id: str,
        sender_id: str,
        reference_id: str,
        notification_type: str,
        content_preview: str,
    ) -> bool:
        """Publish a notification event to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Create the notification payload
            notification = {
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(reference_id),
                "notification_type": notification_type,
                "content_preview": content_preview,
                "timestamp": datetime.now().isoformat(),
                "notification_id": str(ObjectId()),
                "read": False
            }
            
            # Wrap in the expected format for socket_server.py
            message = json.dumps({
                "notification": notification
            })
            
            await self.rabbitmq.publish_message(
                exchange="notification_events",
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
            notification = {
                "event_type": "friend_request",
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(connection_id),
                "content_preview": f"{sender_name} sent you a friend request",
                "timestamp": datetime.now().isoformat(),
                # Add notification_id field for frontend tracking
                "notification_id": str(ObjectId()),
                "read": False,
                "notification_type": "friend_request"
            }
            
            # Wrap in the expected format
            message = json.dumps({
                "notification": notification
            })
            
            await self.rabbitmq.publish_message(
                exchange="connection_events",
                routing_key=f"connection.friend_request",
                message=message
            )
            
            logger.info(f"Published friend request notification for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request notification: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and await self.rabbitmq.is_connected()