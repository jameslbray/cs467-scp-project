import json
import logging
from datetime import datetime

from services.chat.app.db.chat_repository import ChatRepository
from services.chat.app.db.mongo import get_db
from services.chat.app.models.message import Message
from services.rabbitmq.core.client import RabbitMQClient

logger = logging.getLogger(__name__)


class ChatRabbitMQClient:
    def __init__(self):
        self.client = RabbitMQClient()
        self.exchange_name = "chat_exchange"
        self.message_queue = "chat_messages"
        self.notification_queue = "chat_notifications"
        self.user_events_exchange = "user_events"
        self.user_events_queue = "user_events"
        self.user_add_to_room_routing_key = "user.add_to_room"

    async def initialize(self):
        """
        Initialize RabbitMQ connection and declare necessary queues/exchanges
        """
        try:
            await self.client.connect()
            # Declare the exchanges
            await self.client.declare_exchange(
                self.exchange_name, exchange_type="direct"
            )
            await self.client.declare_exchange(
                self.user_events_exchange, exchange_type="topic"
            )
            # Declare queues
            await self.client.declare_queue(self.message_queue)
            await self.client.declare_queue(self.notification_queue)
            await self.client.declare_queue(self.user_events_queue)
            # Bind the user_events queue to the exchange with the routing key
            await self.client.bind_queue(
                self.user_events_queue,
                self.user_events_exchange,
                self.user_add_to_room_routing_key,
            )
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
        """Consume both chat messages and user events from RabbitMQ and process accordingly."""

        async def unified_handler(message):
            try:
                body = json.loads(message.body.decode())
                routing_key = getattr(message, "routing_key", None)
                logger.info(
                    f"Received message with routing key: {routing_key}, body: {body}"
                )

                # Handle user events
                if (
                    routing_key == self.user_add_to_room_routing_key
                    or body.get("event") == "add_user_to_room"
                ):
                    user_id = body["user_id"]
                    room_id = body["room_id"]
                    repo = ChatRepository()
                    updated_room = await repo.add_user_to_room(
                        room_id, user_id
                    )
                    if updated_room:
                        logger.info(
                            f"Added user {user_id} to room {room_id} via user_events queue."
                        )
                    else:
                        logger.warning(
                            f"Failed to add user {user_id} to room {room_id} (room may not exist or user already present)."
                        )
                    await message.ack()
                    return

                # Handle chat messages
                if all(k in body for k in ("room_id", "sender_id", "content")):
                    db = get_db()
                    timestamp = body.get("timestamp")
                    if timestamp:
                        timestamp = datetime.fromtimestamp(timestamp)
                    else:
                        timestamp = datetime.now()
                    msg = Message(
                        id=body.get("id") or "",
                        room_id=body["room_id"],
                        sender_id=body["sender_id"],
                        content=body["content"],
                        created_at=timestamp,
                        updated_at=timestamp,
                        is_edited=body.get("is_edited", False),
                    )
                    await db.messages.insert_one(msg.model_dump(by_alias=True))
                    logger.info(
                        f"Stored chat message in room {msg.room_id} from sender {msg.sender_id}"
                    )
                    await message.ack()
                    return

                logger.warning(f"Unhandled message: {body}")
                await message.ack()
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                await message.nack(requeue=False)

        # Consume from both queues
        await self.client.consume(
            queue_name=self.message_queue, callback=unified_handler
        )
        await self.client.consume(
            queue_name=self.user_events_queue, callback=unified_handler
        )

    async def close(self):
        """Close RabbitMQ connection"""
        try:
            await self.client.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
            raise

    async def consume_all_events(self):
        """Consume all events from RabbitMQ"""
        await self.consume_messages()
