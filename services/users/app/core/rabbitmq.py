from rabbitmq_client import RabbitMQClient
import logging
import json

logger = logging.getLogger(__name__)


class UserRabbitMQClient:
    def __init__(self):
        self.client = RabbitMQClient()
        self.exchange_name = "user_exchange"
        self.user_events_queue = "user_events"
        self.notification_queue = "user_notifications"

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
            await self.client.declare_queue(self.user_events_queue)
            await self.client.declare_queue(self.notification_queue)
            logger.info("RabbitMQ client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ client: {str(e)}")
            raise

    async def publish_user_event(self, event_type: str, user_data: dict):
        """Publish a user-related event"""
        try:
            message = {
                "event_type": event_type,
                "user_data": user_data
            }
            await self.client.publish_message(
                self.exchange_name,
                self.user_events_queue,
                json.dumps(message)
            )
            logger.info(f"User event published: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish user event: {str(e)}")
            raise

    async def publish_notification(self, notification: str):
        """Publish a user notification"""
        try:
            await self.client.publish_message(
                self.exchange_name,
                self.notification_queue,
                notification
            )
            logger.info("User notification published")
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
