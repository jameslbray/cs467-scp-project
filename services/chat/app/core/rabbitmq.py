import json
import logging
from datetime import datetime

from services.chat.app.db.mongo import get_db
from services.chat.app.db.nosql_models.message_log import MessageLog
from services.rabbitmq.core.client import RabbitMQClient

logger = logging.getLogger(__name__)


class ChatRabbitMQClient:
    def __init__(self):
        self.client = RabbitMQClient()
        self.exchange_name = "chat_exchange"
        self.message_queue = "chat_messages"
        self.notification_queue = "chat_notifications"

    async def initialize(self):
        """
        Initialize RabbitMQ connection and declare necessary queues/exchanges
        """
        try:
            await self.client.connect()
            # Declare the exchange
            await self.client.declare_exchange(
                self.exchange_name, exchange_type="direct"
            )
            # Declare queues
            await self.client.declare_queue(self.message_queue)
            await self.client.declare_queue(self.notification_queue)
            logger.info("RabbitMQ client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ client: {str(e)}")
            raise

    async def publish_message(self, message: str, routing_key: str):
        """Publish a chat message"""
        try:
            await self.client.publish_message(
                self.exchange_name, routing_key, message
            )
            logger.info(f"Message published to {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    async def publish_notification(self, notification: str):
        """Publish a chat notification"""
        try:
            await self.client.publish_message(
                self.exchange_name, self.notification_queue, notification
            )
            logger.info("Notification published")
        except Exception as e:
            logger.error(f"Failed to publish notification: {str(e)}")
            raise

    async def consume_messages(self):
        """Consume chat messages from RabbitMQ and store them in MongoDB."""

        async def message_handler(message):
            try:
                body = json.loads(message.body.decode())
                db = get_db()
                # Convert timestamp if present, else use now
                timestamp = body.get("timestamp")
                if timestamp:
                    timestamp = datetime.fromtimestamp(timestamp)
                else:
                    timestamp = datetime.now()
                message_log = MessageLog(
                    room_id=body["room_id"],
                    sender_id=body["sender_id"],
                    content=body["content"],
                    timestamp=timestamp,
                )
                await db.message_logs.insert_one(
                    message_log.model_dump(by_alias=True)
                )
                await message.ack()
            except Exception as e:
                logger.error(f"Failed to process chat message: {e}")
                await message.nack(requeue=False)

        await self.client.consume(
            queue_name=self.message_queue, callback=message_handler
        )

    async def close(self):
        """Close RabbitMQ connection"""
        try:
            await self.client.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
            raise
