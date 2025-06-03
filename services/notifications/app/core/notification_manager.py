"""
Notification manager for handling user notification state.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from services.shared.utils.retry import CircuitBreaker, with_retry

from ..db.models import (
    DeliveryType,
    NotificationDB,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
)
from .notification_rabbitmq import NotificationRabbitMQClient

# configure logging
logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages user notification state."""

    def __init__(
        self,
        config: dict[str, Any],
        rabbitmq_client: NotificationRabbitMQClient,
    ):
        """Initialize the notification manager.

        Args:
            config: Configuration dictionary containing RabbitMQ settings
            socket_server: Optional Socket.IO server instance
        """
        self.config = config
        self._initialized = False
        self.mongo_client: Optional[AsyncIOMotorClient] = None

        # Initialize RabbitMQ client
        self.rabbitmq_client = rabbitmq_client

        # Initialize circuit breaker
        self.db_cb = CircuitBreaker(
            "mongodb", failure_threshold=3, reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the notification manager."""
        if self._initialized:
            logger.warning("Notification manager already initialized")
            return

        try:
            # Register message handlers for all notification types
            await self.rabbitmq_client.register_chat_consumer(
                self._process_chat_notification
            )
            await self.rabbitmq_client.register_notification_consumer(
                self._process_notification
            )
            await self.rabbitmq_client.register_connection_consumer(
                self._process_connection
            )
            logger.info(
                "RabbitMQ client initialized and message handlers registered"
            )

            # Initialize database connection with circuit breaker
            if "mongodb" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb,
                )

            self._initialized = True
            logger.info("Notification manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize notification manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the notification manager."""
        try:
            # Shutdown RabbitMQ client
            await self.rabbitmq_client.shutdown()

            if self.mongo_client is not None:
                await self.mongo_client.close()
                logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self.mongo_client = None
            logger.info("Notification manager shut down")

    async def _connect_database(self) -> None:
        """Connect to MongoDB."""
        # Connect to PostgreSQL
        config = self.config["mongodb"].copy()

        client = AsyncIOMotorClient(config["uri"])
        try:
            # Verify connection
            self.mongo_client = client

            conn_result = await self.check_connection_health()

            if not conn_result:
                raise Exception("Failed to connect to MongoDB")

            db_name = config.get("database", "notifications")
            db = client[db_name]

            # Create indexes for the notifications collection
            await db.notifications.create_index([("recipient_id", 1)])

            # List collections in the database (not on the client)
            collections = await db.list_collection_names()

            # Create notifications collection if it doesn't exist
            if "notifications" not in collections:
                logger.info("Creating notifications collection")
                await db.create_collection("notifications")

            else:
                logger.info("Notifications collection already exists")

            count = await db.notifications.count_documents({})
            logger.info(f"Found {count} existing notifications in database")

            if count == 0:
                # Only create test notification if collection is empty
                logger.info(
                    "No notifications found, creating test notification"
                )
                test_notification = NotificationRequest(
                    recipient_id="550e8400-e29b-41d4-a716-446655440000",
                    sender_id="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    reference_id="123e4567-e89b-12d3-a456-426614174111",
                    content_preview="Hello World!",
                    timestamp=datetime.now().isoformat(),
                    status=DeliveryType.UNDELIVERED,
                    error=None,
                )
                # Convert to database model and save to MongoDB
                db_notification = test_notification.to_db_model()
                result = await db.notifications.insert_one(
                    db_notification.to_mongo_dict()
                )

                # Verify the document was inserted
                doc = await db.notifications.find_one(
                    {"recipient_id": "550e8400-e29b-41d4-a716-446655440000"}
                )
                if doc:
                    logger.info(
                        f"Test notification inserted with ID: {result.inserted_id}"
                    )
                else:
                    logger.warning("Failed to insert test notification")
            else:
                logger.info(
                    f"Skipping test notification creation, database already contains {count} notifications"
                )

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def check_connection_health(self):
        try:
            await self.mongo_client.admin.command("ping")
            return True
        except Exception:
            logger.error("MongoDB connection failed")
            return False

    async def get_user_notifications(
        self, user_id: str
    ) -> List[NotificationResponse]:
        """Get user's notifications."""
        # Default values
        empty_notifications: List[NotificationResponse] = []

        # Fetch from database if not in cache
        user_notifications = await self._get_user_notifications(user_id)
        if user_notifications:
            return user_notifications

        return empty_notifications

    async def _get_user_notifications(
        self, user_id: str
    ) -> list[NotificationResponse] | None:
        """Get user notifications from database."""
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return None

        try:
            if isinstance(user_id, UUID):
                user_id = str(user_id)

            logger.debug(
                f"Searching for notifications with recipient_id: {user_id}"
            )

            # Get the database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]

            stats = await db.command("collStats", "notifications")
            logger.debug(f"Collection stats: {stats}")

            # Query for user notifications
            query = {"recipient_id": user_id}
            cursor = db.notifications.find(query)
            documents = await cursor.to_list(
                length=None
            )  # Fetch all documents into a list
            logger.debug(
                f"Found {len(documents)} notifications for user {user_id}"
            )

            # Process each document into response objects
            notifications = []
            for doc in documents:
                try:
                    # Convert MongoDB doc to database model
                    db_notification = NotificationDB.from_mongo_doc(doc)

                    # Convert database model to API response
                    api_notification = db_notification.to_api_response()
                    notifications.append(api_notification)
                except Exception as doc_error:
                    # Log error but continue processing other documents
                    logger.error(
                        f"Error processing notification document: {doc_error}"
                    )

            return notifications

        except ValueError:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return None

    async def create_notification(
        self, notification: NotificationRequest
    ) -> None:
        """Create a new notification."""
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return

        try:
            # Convert API request to database model
            db_notification = notification.to_db_model()

            # Get database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]

            # Convert to MongoDB document and insert
            mongo_dict = db_notification.to_mongo_dict()
            result = await db.notifications.insert_one(mongo_dict)

            # Log with the actual ObjectId from MongoDB
            logger.info(f"Notification inserted with ID: {result.inserted_id}")

            # Add the ObjectId to the notification for consistency
            from_db = NotificationDB.from_mongo_doc(mongo_dict)
            from_db.id = result.inserted_id

            # Publish to RabbitMQ
            await self.rabbitmq_client.publish_notification(from_db.to_dict())

            logger.info(f"Published notification to RabbitMQ: {notification}")

            # Return all notifications for the recipient
            return

        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return

    async def mark_notification_as_read(
        self, notification_id: str, user_id: str
    ) -> bool:
        """Mark a notification as read.

        Args:
            notification_id: The ID of the notification to mark as read
            user_id: The user ID who owns the notification

        Returns:
            bool: True if update was successful, False otherwise
        """
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return False

        try:
            # Get database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]

            try:
                object_id = ObjectId(notification_id)
            except Exception as e:
                logger.error(
                    f"Invalid ObjectId format: {notification_id}, error: {e}"
                )
                return False

            # Create query with both notification_id and user_id for security
            query = {
                "_id": object_id,  # Use ObjectId, not string
                "recipient_id": user_id,
            }

            # Update document to mark as read
            update = {
                "$set": {
                    "read": True,
                }
            }

            # Update the document directly
            result = await db.notifications.update_one(query, update)

            # Check if update was successful
            if result.modified_count == 1:
                logger.info(
                    f"Notification {notification_id} marked as read for user {user_id}"
                )
                return True
            else:
                # Check if document exists but wasn't modified (already read)
                doc = await db.notifications.find_one({"_id": object_id})
                if doc:
                    logger.info(
                        f"Notification {notification_id} exists but is already read"
                    )
                    return True
                logger.warning(
                    f"Notification {notification_id} not found for user {user_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False

    async def mark_all_notifications_as_read(self, user_id: str) -> bool:
        """Mark all of a user's notification as read.

        Args:
            user_id: The user ID who owns the notification

        Returns:
            bool: True if update was successful, False otherwise
        """
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return False

        try:
            # Get database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]

            # Create query with both notification_id and user_id for security
            query = {"recipient_id": user_id}

            # Update document to mark as read
            update = {
                "$set": {
                    "read": True,
                }
            }

            # Update the document directly
            result = await db.notifications.update_many(query, update)

            # Check if update was successful
            if result.modified_count > 0:
                logger.info(
                    f"All notifications marked as read for user {user_id}"
                )
                return True
            else:
                # Check if document exists but wasn't modified (already read)
                doc = await db.notifications.find_one(
                    {"recipient_id": user_id}
                )
                if doc:
                    logger.info("Notifications exists but are already read")
                    return True
                logger.warning(f"Notification not found for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False

    async def delete_read_notifications(self, user_id: str) -> int:
        """Delete all read notifications for a user.

        Returns:
            int: Number of notifications deleted
        """
        if not self.mongo_client:
            return 0

        try:
            db = self.mongo_client[
                self.config["mongodb"].get("database", "notifications")
            ]
            result = await db.notifications.delete_many(
                {"recipient_id": user_id, "read": True}
            )
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete read notifications: {e}")
            return 0

    async def publish_friend_request_notification(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
        sender_name: str,
    ) -> bool:
        """Publish a friend request notification event to RabbitMQ."""
        return await self.rabbitmq_client.publish_friend_request(
            recipient_id, sender_id, connection_id, sender_name
        )

    async def create_friend_request_notification(
        self,
        recipient_id: str,
        sender_id: str,
        connection_id: str,
    ) -> bool:
        """Create a friend request notification directly in the database."""
        try:
            notification_request = NotificationRequest(
                recipient_id=recipient_id,
                sender_id=sender_id,
                reference_id=str(connection_id),
                content_preview="You have a new friend request",
                notification_type=NotificationType.FRIEND_REQUEST,
                timestamp=datetime.now().isoformat(),
                status=DeliveryType.UNDELIVERED,
                error=None,
            )

            await self.create_notification(notification_request)
            logger.info(
                f"Created friend request notification for recipient {recipient_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create friend request notification: {e}")
            return False

    async def _process_notification(self, message) -> None:
        """Process a general notification message from RabbitMQ."""
        try:
            # Parse the message body
            body = json.loads(message.body.decode())
            if "source" in body and body["source"] == "notifications":
                # Ignore notifications from our own service
                await message.ack()
                logger.info("Ignoring notification from own service")
                return

            logger.info(f"Received general notification: {body}")

            # Extract notification fields
            recipient_id = body.get("recipient_id")
            sender_id = body.get("sender_id")
            reference_id = body.get("reference_id", "")
            content_preview = body.get(
                "content_preview", "New message received"
            )
            notification_type = body.get("notification_type", "system")
            timestamp = body.get("timestamp", datetime.now().isoformat())

            # Validate required fields
            if not recipient_id:
                logger.error(
                    f"Missing required recipient_ids in notification: {body}"
                )
                await message.nack(
                    requeue=False
                )  # Don't requeue malformed messages
                return

            # Create notification for all specified recipients
            notification_request = NotificationRequest(
                recipient_id=recipient_id,
                sender_id=sender_id,
                reference_id=reference_id,
                content_preview=content_preview,
                notification_type=notification_type,
                timestamp=timestamp,
                status=DeliveryType.UNDELIVERED,
                error=None,
            )
            await self.create_notification(notification_request)
        except Exception as inner_e:
            # Log error but continue with other recipients
            logger.error(
                f"Failed to create notification for recipient {recipient_id}: {inner_e}"
            )

            logger.info(f"Created {recipient_id} notification")
            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in general notification message: {e}")
            await message.nack(requeue=False)  # Don't requeue invalid JSON

        except Exception as e:
            logger.error(f"Error processing general notification: {e}")
            # Implement retry logic with headers
            headers = message.headers or {}
            retry_count = headers.get("x-retry-count", 0)
            if retry_count < 3:  # Maximum 3 retries
                headers["x-retry-count"] = retry_count + 1
                await message.nack(requeue=True, headers=headers)
            else:
                logger.warning(
                    f"General notification failed after {retry_count} retries, not requeuing"
                )
                await message.nack(requeue=False)

    async def _process_user_notification(self, message) -> None:
        """Process a user-specific notification message from RabbitMQ."""
        try:
            # Parse the message body
            body = json.loads(message.body.decode())
            logger.info(f"Received user notification: {body}")

            # Extract notification fields
            recipient_id = body.get("recipient_id")
            sender_id = body.get("sender_id", "system")
            reference_id = body.get("reference_id", "")
            content_preview = body.get("content_preview", "")
            notification_type = body.get("notification_type", "user")
            timestamp = body.get("timestamp", datetime.now().isoformat())

            # Validate required fields
            if not recipient_id:
                logger.error(
                    f"Missing required recipient_id in user notification: {body}"
                )
                await message.nack(
                    requeue=False
                )  # Don't requeue malformed messages
                return

            # Create notification for the user
            notification_request = NotificationRequest(
                recipient_id=recipient_id,
                sender_id=sender_id,
                reference_id=reference_id,
                content_preview=content_preview,
                notification_type=notification_type,
                timestamp=timestamp,
                status=DeliveryType.UNDELIVERED,
                error=None,
            )

            await self.create_notification(notification_request)
            logger.info(
                f"Created user notification for recipient {recipient_id}"
            )
            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in user notification message: {e}")
            await message.nack(requeue=False)  # Don't requeue invalid JSON

        except Exception as e:
            logger.error(f"Error processing user notification: {e}")
            # Implement retry logic with headers
            headers = message.headers or {}
            retry_count = headers.get("x-retry-count", 0)
            if retry_count < 3:  # Maximum 3 retries
                headers["x-retry-count"] = retry_count + 1
                await message.nack(requeue=True, headers=headers)
            else:
                logger.warning(
                    f"User notification failed after {retry_count} retries, not requeuing"
                )
                await message.nack(requeue=False)

    async def _process_connection(self, message) -> None:
        """Process a connection notification message from RabbitMQ."""
        try:
            # Parse the message body
            body = json.loads(message.body.decode())
            logger.info(f"Received connection notification: {body}")

            # Extract common fields
            recipient_id = body.get("recipient_id")
            sender_id = body.get("sender_id")
            reference_id = body.get("reference_id")
            timestamp = body.get("timestamp", datetime.now().isoformat())

            # Validate required fields
            if not recipient_id or not sender_id:
                logger.error(
                    f"Missing required fields in connection notification: {body}"
                )
                await message.nack(
                    requeue=False
                )  # Don't requeue malformed messages
                return

            # Handle different connection event types
            event_type = body.get("event_type")

            if event_type == "friend_request":
                # Create a notification for a new friend request
                notification_request = NotificationRequest(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    reference_id=reference_id,
                    content_preview=body.get(
                        "content_preview", "You received a new friend request"
                    ),
                    notification_type=NotificationType.FRIEND_REQUEST,
                    timestamp=timestamp,
                    status=DeliveryType.UNDELIVERED,
                    error=None,
                )
                await self.create_notification(notification_request)
                logger.info(
                    f"Created friend request notification for {recipient_id} from {sender_id}"
                )

            elif event_type == "friend_accepted":
                # Create a notification for an accepted friend request
                notification_request = NotificationRequest(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    reference_id=reference_id,
                    content_preview=body.get(
                        "content_preview", "Your friend request was accepted"
                    ),
                    notification_type=NotificationType.FRIEND_ACCEPTED,
                    timestamp=timestamp,
                    status=DeliveryType.UNDELIVERED,
                    error=None,
                )
                await self.create_notification(notification_request)
                logger.info(
                    f"Created friend acceptance notification for {recipient_id} from {sender_id}"
                )

            elif event_type == "friend_removed":
                # Handle friend removal, typically no notification needed
                logger.debug(
                    "Received friend removal event - no notification created"
                )

            else:
                # Log unknown event types but acknowledge the message
                logger.warning(f"Unknown connection event type: {event_type}")

            # Acknowledge successful processing
            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            await message.nack(requeue=False)  # Don't requeue invalid JSON

        except Exception as e:
            logger.error(f"Error processing connection notification: {e}")
            # Requeue the message for retry unless it's been retried too many times
            # You might want to check message headers for retry count
            headers = message.headers or {}
            retry_count = headers.get("x-retry-count", 0)
            if retry_count < 3:  # Maximum 3 retries
                # Add retry count to headers
                headers["x-retry-count"] = retry_count + 1
                await message.nack(requeue=True, headers=headers)
            else:
                # Too many retries, don't requeue
                logger.warning(
                    f"Message failed after {retry_count} retries, not requeuing"
                )
                await message.nack(requeue=False)

    async def _process_chat_notification(self, message) -> None:
        """Process a message notification from RabbitMQ."""
        try:
            # Parse the message body
            body = json.loads(message.body.decode())
            logger.info(f"Received message notification: {body}")

            # Extract notification fields
            recipient_ids = body.get("recipient_ids")
            sender_id = body.get("sender_id")
            room_id = body.get("room_id", "")
            content_preview = body.get(
                "content_preview", "You've been added to a new chat"
            )
            timestamp = body.get("timestamp", datetime.now().isoformat())

            # Validate required fields
            if not recipient_ids or not sender_id:
                logger.error(
                    f"Missing required fields in message notification: {body}"
                )
                await message.nack(
                    requeue=False
                )  # Don't requeue malformed messages
                return

            # Truncate content preview if too long
            if len(content_preview) > 100:
                content_preview = content_preview[:97] + "..."

            # Create notification for each message recipient
            for recipient_id in recipient_ids:
                if recipient_id == sender_id:
                    continue  # Skip notifications to self
                notification_request = NotificationRequest(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    reference_id=room_id,
                    content_preview=content_preview,
                    notification_type=NotificationType.NEW_MESSAGE,
                    timestamp=timestamp,
                    status=DeliveryType.UNDELIVERED,
                    error=None,
                )
                await self.create_notification(notification_request)
                logger.info(
                    f"Created message notification for recipient "
                    f"{recipient_id} from {sender_id}"
                )
            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message notification: {e}")
            await message.nack(requeue=False)  # Don't requeue invalid JSON

        except Exception as e:
            logger.error(f"Error processing message notification: {e}")
            # Implement retry logic with headers
            headers = message.headers or {}
            retry_count = headers.get("x-retry-count", 0)
            if retry_count < 3:  # Maximum 3 retries
                headers["x-retry-count"] = retry_count + 1
                await message.nack(requeue=True, headers=headers)
            else:
                logger.warning(
                    f"Message notification failed after {retry_count} retries, not requeuing"
                )
                await message.nack(requeue=False)
