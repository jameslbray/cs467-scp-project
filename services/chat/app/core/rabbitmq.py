import json
import logging
from datetime import datetime
import uuid

from services.chat.app.db.chat_repository import ChatRepository
from services.chat.app.db.mongo import get_db
from services.chat.app.models.message import Message
from services.rabbitmq.core.client import RabbitMQClient

logger = logging.getLogger(__name__)


class ChatRabbitMQClient:
    def __init__(self):
        self.client = RabbitMQClient()
        self.exchange_name = "chat"
        self.message_queue = "chat_messages"
        self.notification_queue = "chat_notifications"
        self.user_events_exchange = "user"
        self.user_events_queue = "user"
        self.user_add_to_room_routing_key = "user.add_to_room"
        self.room_rpc = "room_rpc"
        self.room_get_id_routing_key = "room.get_id_by_name"
        self.room_is_user_member_routing_key = "room.is_user_member"

    async def initialize(self):
        await self.client.connect()
        await self.client.declare_exchange(
            self.exchange_name, exchange_type="topic"
        )
        await self.client.declare_exchange(
            self.user_events_exchange, exchange_type="topic"
        )
        await self.client.declare_queue(self.message_queue)
        await self.client.declare_queue(self.notification_queue)
        await self.client.declare_queue(self.user_events_queue)
        await self.client.declare_queue(self.room_rpc)
        await self.client.bind_queue(
            self.message_queue, self.exchange_name, "#"
        )
        await self.client.bind_queue(
            self.room_rpc, self.exchange_name, self.room_get_id_routing_key
        )
        await self.client.bind_queue(
            self.room_rpc,
            self.exchange_name,
            self.room_is_user_member_routing_key,
        )
        await self.client.bind_queue(
            self.user_events_queue,
            self.user_events_exchange,
            self.user_add_to_room_routing_key,
        )
        logger.info("RabbitMQ client initialized successfully")

    async def publish_message(self, message: str, routing_key: str):
        await self.client.publish_message(
            self.exchange_name, routing_key, message
        )
        logger.info(f"Message published to {routing_key}")

    async def publish_notification(self, notification: str):
        await self.client.publish_message(
            self.exchange_name, self.notification_queue, notification
        )
        logger.info("Notification published")

    async def consume_messages(self):
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

                # Handle room RPC requests: get_room_id_by_name
                if (
                    routing_key == self.room_get_id_routing_key
                    or body.get("action") == "get_room_id_by_name"
                ):
                    name = body.get("name")
                    repo = ChatRepository()
                    room_id = await repo.get_room_id_by_name(name)
                    response = (
                        {"room_id": room_id}
                        if room_id
                        else {"error": "Room not found"}
                    )
                    await self.client.publish_message(
                        exchange="",
                        routing_key=message.reply_to,
                        message=json.dumps(response),
                        correlation_id=message.correlation_id,
                    )
                    await message.ack()
                    return

                # Handle room RPC requests: is_user_member
                if (
                    routing_key == self.room_is_user_member_routing_key
                    or body.get("action") == "is_user_member"
                ):
                    room_id = body.get("room_id")
                    user_id = body.get("user_id")
                    repo = ChatRepository()
                    is_member = await repo.is_user_member(room_id, user_id)
                    response = {"is_member": is_member}
                    await self.client.publish_message(
                        exchange="",
                        routing_key=message.reply_to,
                        message=json.dumps(response),
                        correlation_id=message.correlation_id,
                    )
                    await message.ack()
                    return

                # Handle chat messages
                if all(k in body for k in ("room_id", "sender_id", "content")):
                    db = get_db()
                    if db is None:
                        logger.error("Database connection is not initialized.")
                        await message.nack(requeue=False)
                        return
                    timestamp = body.get("timestamp")
                    if timestamp:
                        timestamp = datetime.fromtimestamp(timestamp)
                    else:
                        timestamp = datetime.now()
                    msg = Message(
                        _id=body.get("id") or str(uuid.uuid4()),
                        room_id=body["room_id"],
                        sender_id=body["sender_id"],
                        content=body["content"],
                        created_at=timestamp,
                        updated_at=timestamp,
                        is_edited=body.get("is_edited", False),
                    )
                    logger.info(
                        f"Attempting to insert message into DB: {msg.model_dump(by_alias=True)}"
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

        await self.client.consume(
            queue_name=self.message_queue, callback=unified_handler
        )
        await self.client.consume(
            queue_name=self.user_events_queue, callback=unified_handler
        )
        await self.client.consume(
            queue_name=self.room_rpc, callback=unified_handler
        )

    async def close(self):
        await self.client.close()

    async def consume_all_events(self):
        await self.consume_messages()
