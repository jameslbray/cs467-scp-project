from rabbitmq_client import RabbitMQClient, Settings
import logging

logger = logging.getLogger(__name__)


class ChatRabbitMQClient:
    def __init__(self):
        self.client = RabbitMQClient()
        self.exchange_name = "chat_exchange"
        self.message_queue = "chat_messages"
        self.notification_queue = "chat_notifications"

    async def initialize(self):
        """Initialize RabbitMQ connection and declare necessary queues/exchanges"""
        try:
            await self.client.connect()
            # Declare the exchange
            await self.client.declare_exchange(
                self.exchange_name,
                exchange_type="direct"
            )
            # Declare queues
            await self.client.declare_queue(self.message_queue)
            await self.client.declare_queue(self.notification_queue)
            logger.info("RabbitMQ client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ client: {str(e)}")
            raise

    async def publish_message(self, message: str, routing_key: str = None):
        """Publish a chat message"""
        try:
            routing_key = routing_key or self.message_queue
            await self.client.publish_message(
                self.exchange_name,
                routing_key,
                message
            )
            logger.info(f"Message published to {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    async def publish_notification(self, notification: str):
        """Publish a chat notification"""
        try:
            await self.client.publish_message(
                self.exchange_name,
                self.notification_queue,
                notification
            )
            logger.info("Notification published")
        except Exception as e:
            logger.error(f"Failed to publish notification: {str(e)}")
            raise

    async def close(self):
        """Close RabbitMQ connection"""
        try:
            await self.client.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
            raise
