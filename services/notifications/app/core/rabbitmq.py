# Import from local rabbitmq client implementation
import json
import logging
from typing import Any, Dict, Optional, cast

from sqlalchemy.orm import Session

from services.db_init.app.models import User as UserModel
from services.rabbitmq.core.client import RabbitMQClient
from services.rabbitmq.core.config import Settings as RabbitMQSettings

from ..db.database import get_db
from ..schemas import User
from . import security
from .config import Settings

# Configure logging
logger = logging.getLogger("notifications.rabbitmq")

# TODO: Figure this out

class NotificationRabbitMQClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        # Convert UserSettings to RabbitMQSettings
        rabbitmq_settings = RabbitMQSettings(
            RABBITMQ_URL=settings.RABBITMQ_URL,
            RABBITMQ_HOST=settings.RABBITMQ_HOST,
            RABBITMQ_PORT=settings.RABBITMQ_PORT,
            RABBITMQ_USER=settings.RABBITMQ_USER,
            RABBITMQ_PASSWORD=settings.RABBITMQ_PASSWORD,
            RABBITMQ_VHOST=settings.RABBITMQ_VHOST
        )
        self.rabbitmq_client = RabbitMQClient(rabbitmq_settings)
        logger.info(
            "[RabbitMQ] Client initialized with URL: %s",
            settings.RABBITMQ_URL
        )

    async def connect(self):
        """Connect to RabbitMQ and set up exchanges/queues"""
        logger.info("[RabbitMQ] Establishing connection...")
        await self.rabbitmq_client.connect()

        # Declare auth exchange
        logger.info("[RabbitMQ] Declaring auth exchange...")
        await self.rabbitmq_client.declare_exchange("auth", "topic")
        logger.info("[RabbitMQ] Auth exchange declared")

        # Declare user_events exchange for presence updates
        logger.info("[RabbitMQ] Declaring user_events exchange...")
        await self.rabbitmq_client.declare_exchange("user_events", "topic")
        logger.info("[RabbitMQ] User events exchange declared")

        # Declare auth queue
        logger.info("[RabbitMQ] Declaring auth queue...")
        await self.rabbitmq_client.declare_queue("auth_queue")
        logger.info("[RabbitMQ] Auth queue declared")

        # Bind queue to exchange with routing keys
        routing_keys = [
            "auth.register",
            "auth.login",
            "auth.logout",
            "auth.validate"
        ]
        for key in routing_keys:
            await self.rabbitmq_client.bind_queue("auth_queue", "auth", key)
            logger.info(f"[RabbitMQ] Bound queue to '{key}' routing key")

        # Start consuming messages
        await self.consume_messages()
        logger.info("[RabbitMQ] Message consumption started")

    async def consume_messages(self):
        """Start consuming messages from the auth queue"""
        async def message_handler(message):
            try:
                # Parse message
                body = json.loads(message.body.decode())
                routing_key = message.routing_key

                # Process the message
                response = await self.process_auth_message({
                    "routing_key": routing_key,
                    "body": body
                })

                # Acknowledge message
                await message.ack()

                # If there's a reply_to, send response back
                if message.reply_to:
                    await self.rabbitmq_client.publish_message(
                        exchange="",
                        routing_key=message.reply_to,
                        message=json.dumps(response)
                    )

            except Exception as e:
                logger.error(f"[RabbitMQ] Error processing message: {str(e)}")
                # Negative acknowledge in case of error
                await message.nack(requeue=False)

        # Start consuming messages
        await self.rabbitmq_client.consume(
            queue_name="auth_queue",
            callback=message_handler
        )

    async def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: str
    ) -> None:
        """Publish a message to RabbitMQ"""
        try:
            await self.rabbitmq_client.publish_message(
                exchange,
                routing_key,
                message
            )
            logger.info("[RabbitMQ] Message published successfully")
        except Exception as e:
            logger.error("[RabbitMQ] Error publishing message: %s", str(e))
            raise

    async def process_auth_message(
        self,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process incoming auth messages"""
        try:
            routing_key = cast(str, message.get("routing_key"))
            body = cast(Dict[str, Any], message.get("body", {}))

            logger.info(
                "[RabbitMQ] Received message with routing key: %s",
                routing_key
            )
            logger.debug(
                "[RabbitMQ] Message body: %s",
                json.dumps(body, indent=2)
            )

            response = None
            db = next(get_db())

            # Log the type of request being processed
            if routing_key == "auth.register":
                username = body.get('username', 'unknown')
                logger.info(
                    "[RabbitMQ] Processing registration request for user: %s",
                    username
                )
                response = await self.handle_register(body, db)
            elif routing_key == "auth.login":
                username = body.get('username', 'unknown')
                logger.info(
                    "[RabbitMQ] Processing login request for user: %s",
                    username
                )
                response = await self.handle_login(body, db)
            elif routing_key == "auth.logout":
                user_id = body.get('user_id', 'unknown')
                logger.info(
                    "[RabbitMQ] Processing logout request for user ID: %s",
                    user_id
                )
                response = await self.handle_logout(body, db)
            elif routing_key == "auth.validate":
                logger.info("[RabbitMQ] Processing token validation request")
                response = await self.handle_validate(body, db)

            return response

        except Exception as e:
            logger.error("[RabbitMQ] Error processing message: %s", str(e))
            return {
                "error": True,
                "message": str(e)
            }

    async def handle_register(
        self,
        data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Handle user registration"""
        # Check if user exists
        db_user = (
            db.query(UserModel)
            .filter(
                (UserModel.email == data["email"]) |
                (UserModel.username == data["username"])
            )
            .first()
        )
        if db_user is not None:
            return {
                "error": True,
                "message": "Email or Username already registered"
            }

        # Create user
        hashed_password = security.get_password_hash(data["password"])
        db_user = UserModel(
            email=data["email"],
            username=data["username"],
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return {
            "error": False,
            "user": User.model_validate(db_user).model_dump()
        }

    async def handle_validate(
        self,
        data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Handle token validation"""
        token = data.get("token")
        if not token:
            return {
                "error": True,
                "message": "Token not provided"
            }

        try:
            token_data = security.get_token_data(token, db)
            user = (
                db.query(UserModel)
                .filter(UserModel.username == token_data.username)
                .first()
            )

            if not user:
                return {
                    "error": True,
                    "message": "User not found"
                }

            return {
                "error": False,
                "user": User.model_validate(user).model_dump()
            }

        except Exception as e:
            return {
                "error": True,
                "message": str(e)
            }

    async def close(self):
        """Close RabbitMQ connection"""
        await self.rabbitmq_client.close()
