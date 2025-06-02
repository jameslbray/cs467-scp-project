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
            await self.rabbitmq.declare_exchange("connections", "topic")
            await self.rabbitmq.declare_exchange("notifications", "topic")

            # Declare queue for connection events
            await self.rabbitmq.declare_queue(
                "connections",
                durable=True
            )
            
            # Declare queue for connection notifications
            await self.rabbitmq.declare_queue(
                "notifications",
                durable=True
            )

            # Bind queues to exchanges with appropriate routing keys
            await self.rabbitmq.bind_queue(
                "connections",
                "connections",
                "user.#"  # All connection update events
            )
            
            await self.rabbitmq.bind_queue(
                "notifications",
                "notifications",
                "user.#"  # All connection notifications
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
                "connections",
                connection_update_handler
            )
            
            logger.info("Consumer handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register consumer handlers: {e}")
            raise

    async def publish_friend_request(
        self,
        message: str,
        routing_key: str,
        reply_to: Optional[str],
    ) -> bool:
        """Publish a friend request notification event."""
        try:
            if not self._initialized:
                await self.initialize()
            
            if routing_key is None:
                routing_key = "user.friend_request"
            # if reply_to is None:
            #     reply_to = "connection_notifications"
            
            if reply_to is not None:
                await self.rabbitmq.publish_message(
                    exchange="",
                    routing_key=reply_to,
                    message=message,
                )
            else:
                await self.rabbitmq.publish_message(
                    exchange="connections",
                    routing_key=routing_key,
                    message=message
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request notification: {e}")
            return False
            
    async def publish_friend_accepted(
        self,
        exchange: str,
        message: str,
        routing_key: str,
    ) -> bool:
        """Publish a friend acceptance notification event."""
        try:
            if not self._initialized:
                await self.initialize()

            await self.rabbitmq.publish_message(
                exchange=exchange,
                routing_key=routing_key,
                message=message
            )
            
            logger.info(f"Published friend acceptance notification")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend acceptance notification: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and self.rabbitmq.is_connected()

    async def publish_friends_list(
        self,
        message: str,
        routing_key: str,
        correlation_id: str
    ) -> bool:
        """Publish a friend list event."""
        logger.info("Publishing friend list")
        logger.info(f"Message content: {message}")
        logger.info(f"Reply to: {routing_key}, Correlation ID: {correlation_id}")
        try:
            if not self._initialized:
                await self.initialize()
            
            await self.rabbitmq.publish_message(
                exchange="",
                routing_key=routing_key,
                message=message,
                correlation_id=correlation_id
            )

            return True
        except Exception as e:
            logger.error(f"Failed to publish friend list: {e}")
            return False