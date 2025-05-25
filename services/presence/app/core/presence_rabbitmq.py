"""
RabbitMQ client for presence service.
"""
import logging
import json
from typing import Any, Callable, Dict, Optional
from datetime import datetime

from services.rabbitmq.core.client import RabbitMQClient as BaseRabbitMQClient
from services.shared.utils.retry import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)

class PresenceRabbitMQClient:
    """RabbitMQ client for presence service."""

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
            logger.info("RabbitMQ client initialized successfully")
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

            # Declare exchanges with correct types
            await self.rabbitmq.declare_exchange("presence", "direct")  # Match definitions.json
            await self.rabbitmq.declare_exchange("users", "direct")     # Match definitions.json

            # Declare queues matching definitions.json
            await self.rabbitmq.declare_queue(
                "presence",  # Match definitions.json
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "user_events",  # Match definitions.json
                durable=True
            )

            # Bind queues to exchanges with routing keys matching definitions.json
            await self.rabbitmq.bind_queue(
                "presence",
                "presence",
                "updates"  # Match definitions.json
            )
            
            # User events binding
            await self.rabbitmq.bind_queue(
                "user_events",
                "users",
                "events"  # Match definitions.json
            )

            logger.info("Connected to RabbitMQ for presence events")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def register_consumers(
        self, 
        presence_handler: Callable
    ) -> None:
        """Register consumer handler for the presence queue."""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Start consuming messages with provided handler
            await self.rabbitmq.consume(
                "presence",  # Match definitions.json
                presence_handler
            )
            
            logger.info("Consumer handler registered successfully")
        except Exception as e:
            logger.error(f"Failed to register consumer handler: {e}")
            raise

    async def publish_status_update(
        self,
        user_id: str,
        status: str,
        last_status_change: Optional[float] = None
    ) -> bool:
        """Publish a status update to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "type": "status_update",
                "user_id": user_id,
                "status": status,
                "last_status_change": last_status_change or datetime.now().timestamp(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="presence",
                routing_key="updates",
                message=message
            )
            
            logger.info(f"Published status update for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")
            return False

    async def publish_friend_request(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
        sender_name: str,
    ) -> bool:
        """Publish a friend request presence event to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "event_type": "friend_request",
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "reference_id": str(connection_id),
                "content_preview": f"{sender_name} sent you a friend request",
                "timestamp": datetime.now().isoformat(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="connection_events",
                routing_key=f"connection.friend_request",
                message=message
            )
            
            logger.info(f"Published friend request presence for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request presence: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and await self.rabbitmq.is_connected()