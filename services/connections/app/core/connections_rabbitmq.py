"""
RabbitMQ client for connection service.
"""
import json
import logging
from typing import Any, Callable, Dict, Optional
from datetime import datetime

from services.rabbitmq.core.client import RabbitMQClient as BaseRabbitMQClient
from services.shared.utils.retry import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)

class ConnectionsRabbitMQClient:
    """RabbitMQ client for connection service."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the RabbitMQ client."""
        self.config = config or {}
        self.rabbitmq = BaseRabbitMQClient()
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            "rabbitmq",
            failure_threshold=3,
            reset_timeout=30.0
        )
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the RabbitMQ client."""
        if self._initialized:
            logger.warning("RabbitMQ client already initialized")
            return True

        try:
            # Connect to RabbitMQ with retry
            await with_retry(
                self._connect,
                max_attempts=5,
                initial_delay=5.0,
                max_delay=60.0,
                circuit_breaker=self.circuit_breaker
            )
            
            self._initialized = True
            logger.info("Connection RabbitMQ client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ client: {e}")
            self._initialized = False
            return False

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
            await self.rabbitmq.declare_exchange("connection_events", "topic")
            await self.rabbitmq.declare_exchange("notification_events", "topic")
            
            await self.rabbitmq.declare_exchange("notifications", "topic")   

            # Declare queue for connection events
            await self.rabbitmq.declare_queue(
                "connection_updates",
                durable=True
            )
            
            # Declare queue for connection notifications
            await self.rabbitmq.declare_queue(
                "connection_notifications",
                durable=True
            )

            # Bind queues to exchanges with appropriate routing keys
            await self.rabbitmq.bind_queue(
                "connection_updates",
                "connection_events",
                "connection.#"  # All connection update events
            )
            
            await self.rabbitmq.bind_queue(
                "connection_notifications", 
                "notification_events",
                "connection.#"  # All connection notification events
            )
            
            logger.info("Connected to RabbitMQ for connection events")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def register_consumers(
        self, 
        connection_update_handler: Callable
    ) -> None:
        """Register consumer handlers for different queues."""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Start consuming messages with provided handlers
            await self.rabbitmq.consume(
                "connection_updates",
                connection_update_handler
            )
            
            logger.info("Consumer handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register consumer handlers: {e}")
            raise

    async def publish_friend_request(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
        sender_name: str,
    ) -> bool:
        """Publish a friend request notification event."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "event_type": "friend_request",
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(connection_id),
                "notification_type": "friend_request",
                "content_preview": f"{sender_name} sent you a friend request",
                "timestamp": datetime.now().isoformat(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="connection_events",
                routing_key="connection.friend_request",
                message=message
            )
            
            logger.info(f"Published friend request notification for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request notification: {e}")
            return False
            
    async def publish_friend_accepted(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
        accepter_name: str,
    ) -> bool:
        """Publish a friend acceptance notification event."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "event_type": "friend_accepted",
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(connection_id),
                "notification_type": "friend_accepted",
                "content_preview": f"{accepter_name} accepted your friend request",
                "timestamp": datetime.now().isoformat(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="connection_events",
                routing_key="connection.friend_accepted",
                message=message
            )
            
            logger.info(f"Published friend acceptance notification for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend acceptance notification: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and await self.rabbitmq.is_connected()