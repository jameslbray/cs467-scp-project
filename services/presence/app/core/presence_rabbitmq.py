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
            await self.rabbitmq.declare_exchange("presence", "direct")
            await self.rabbitmq.declare_exchange("users", "direct")

            # Declare queues matching updated definitions
            await self.rabbitmq.declare_queue(
                "presence", 
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "presence_updates",
                durable=True
            )
            await self.rabbitmq.declare_queue(
                "user_events",
                durable=True
            )

            # Bind queues with standardized routing keys
            await self.rabbitmq.bind_queue(
                "presence",
                "presence",
                "status.updates"
            )
            
            await self.rabbitmq.bind_queue(
                "presence_updates",
                "presence",
                "status.updates"
            )
            
            await self.rabbitmq.bind_queue(
                "presence",
                "presence", 
                "status.query"
            )
            
            await self.rabbitmq.bind_queue(
                "presence",
                "presence",
                "friend.statuses"
            )
            
            # User events binding
            await self.rabbitmq.bind_queue(
                "user_events",
                "users",
                "events"
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
                "presence",
                presence_handler
            )
            
            await self.rabbitmq.consume(
                "presence_updates", 
                self._handle_presence_updates
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
                "type": "presence:status:update",
                "user_id": user_id,
                "status": status,
                "last_status_change": last_status_change or datetime.now().timestamp(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="presence",
                routing_key="status.updates",
                message=message
            )
            
            logger.info(f"Published status update for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")
            return False

    async def publish_status_query_response(
        self,
        user_id: str,
        status: str,
        last_status_change: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish a status query response to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "type": "presence:status:query:response",
                "user_id": user_id,
                "status": status,
                "last_status_change": last_status_change or datetime.now().timestamp(),
            })
            
            await self.rabbitmq.publish_message(
                exchange="presence",
                routing_key="status.query.response",
                message=message,
                correlation_id=correlation_id
            )
            
            logger.info(f"Published status query response for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish status query response: {e}")
            return False

    async def publish_friend_statuses_response(
        self,
        requesting_user_id: str,
        statuses: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish friend statuses response to RabbitMQ."""
        try:
            if not self._initialized:
                await self.initialize()
                
            message = json.dumps({
                "type": "presence:friend:statuses:response",
                "requesting_user_id": requesting_user_id,
                "statuses": statuses,
                "timestamp": datetime.now().timestamp()
            })
            
            await self.rabbitmq.publish_message(
                exchange="presence",
                routing_key="friend.statuses.response",
                message=message,
                correlation_id=correlation_id
            )
            
            logger.info(f"Published friend statuses response for {requesting_user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend statuses response: {e}")
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
                routing_key="connection.friend_request",
                message=message
            )
            
            logger.info(f"Published friend request presence for recipient {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish friend request presence: {e}")
            return False

    async def _handle_presence_updates(self, message):
        """Handle presence update messages."""
        try:
            body = json.loads(message.body.decode())
            message_type = body.get("type")
            
            logger.info(f"Received presence message: {message_type}")
            
            # Route to appropriate handler based on message type
            if message_type == "presence:status:update":
                await self._handle_status_update(body)
            elif message_type == "presence:status:query":
                await self._handle_status_query(body)
            elif message_type == "presence:friend:statuses":
                await self._handle_friend_statuses_request(body)
            else:
                logger.warning(f"Unknown presence message type: {message_type}")
                
            await message.ack()
        except Exception as e:
            logger.error(f"Error handling presence update: {e}")
            await message.nack(requeue=False)

    async def _handle_status_update(self, data: Dict[str, Any]):
        """Handle status update messages."""
        # This would be implemented by the presence manager
        logger.info(f"Processing status update: {data}")

    async def _handle_status_query(self, data: Dict[str, Any]):
        """Handle status query messages."""
        # This would be implemented by the presence manager
        logger.info(f"Processing status query: {data}")

    async def _handle_friend_statuses_request(self, data: Dict[str, Any]):
        """Handle friend statuses request messages."""
        # This would be implemented by the presence manager
        logger.info(f"Processing friend statuses request: {data}")

    async def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._initialized and await self.rabbitmq.is_connected()