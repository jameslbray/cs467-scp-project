"""
Notification manager for handling user notification state.
"""

import logging
import json
from uuid import UUID
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
# import asyncpg  # type: ignore
# from pymongo import MongoClient

from services.shared.utils.retry import CircuitBreaker, with_retry
# from services.rabbitmq.core.client import RabbitMQClient
from ..db.models import (
    NotificationDB,
    NotificationType,
    NotificationResponse,
    NotificationRequest,
    DeliveryType
)
# from services.socket_io.app.core.socket_server import SocketServer as SocketManager

# configure logging
logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages user notification state."""

    def __init__(
        self,
        config: dict[str, Any],
        # socket_server: Optional[SocketManager] = None
    ):
        """Initialize the notification manager.

        Args:
            config: Configuration dictionary containing RabbitMQ settings
            socket_server: Optional Socket.IO server instance
        """
        self.config = config
        self._initialized = False
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        # self.db_pool: Optional[MongooseClient] = None
        # self.socket_server = socket_server

        # TODO: Decide if we need to keep this in memory or not

        # User notification data
        # self.notification_data: dict[str, dict[str, Any]] = {}

        # Initialize RabbitMQ client
        # self.rabbitmq = RabbitMQClient()

        # Initialize circuit breakers
        # self.rabbitmq_cb = CircuitBreaker(
        #     "rabbitmq",
        #     failure_threshold=3,
        #     reset_timeout=30.0
        # )
        self.db_cb = CircuitBreaker(
            "mongodb",
            failure_threshold=3,
            reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the notification manager."""
        if self._initialized:
            logger.warning("Notification manager already initialized")
            return

        try:
            # Initialize RabbitMQ client with circuit breaker
            # await with_retry(
            #     self._connect_rabbitmq,
            #     max_attempts=5,
            #     initial_delay=5.0,
            #     max_delay=60.0,
            #     circuit_breaker=self.rabbitmq_cb
            # )

            # Initialize database if this is the presence service
            if "mongodb" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb
                )

            self._initialized = True
            logger.info("Notification manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize notification manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the notification manager."""
        # await self.rabbitmq.close()

        try:
            if self.mongo_client is not None:
                await self.mongo_client.close()
                logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
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
            if 'notifications' not in collections:
                logger.info("Creating notifications collection")
                await db.create_collection('notifications')
                
            else:
                logger.info("Notifications collection already exists")
        
            count = await db.notifications.count_documents({})
            logger.info(f"Found {count} existing notifications in database")

            if count == 0:
                # Only create test notification if collection is empty
                logger.info("No notifications found, creating test notification")
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
                result = await db.notifications.insert_one(db_notification.to_mongo_dict())
                
                # Verify the document was inserted
                doc = await db.notifications.find_one({"recipient_id": "550e8400-e29b-41d4-a716-446655440000"})
                if doc:
                    logger.info(f"Test notification inserted with ID: {result.inserted_id}")
                else:
                    logger.warning("Failed to insert test notification")
            else:
                logger.info(f"Skipping test notification creation, database already contains {count} notifications")
            

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def check_connection_health(self):
        try:
            await self.mongo_client.admin.command('ping')
            return True
        except Exception:
            logger.error("MongoDB connection failed")
            return False

    # async def _connect_rabbitmq(self) -> None:
    #     """Connect to RabbitMQ."""
    #     try:
    #         # Connect to RabbitMQ using the shared client
    #         connected = await self.rabbitmq.connect()
    #         if not connected:
    #             raise Exception("Failed to connect to RabbitMQ")

    #         # Declare exchange
    #         await self.rabbitmq.declare_exchange("notification_events", "topic")
    #         await self.rabbitmq.declare_exchange("user_events", "topic")

    #         # Declare and bind queue
    #         await self.rabbitmq.declare_queue(
    #             "general_notifications",
    #             durable=True
    #         )
    #         await self.rabbitmq.declare_queue(
    #             "user_notifications",
    #             durable=True
    #         )
    #         await self.rabbitmq.declare_queue(
    #             "friend_requests",
    #             durable=True
    #         )

    #         # Bind queue to exchange with routing key
    #         # General notifications for all users
    #         await self.rabbitmq.bind_queue(
    #             "general_notifications",
    #             "notification_events",
    #             "broadcast.#"  # All broadcast messages
    #         )

    #         # User-specific notifications
    #         await self.rabbitmq.bind_queue(
    #             "user_notifications",
    #             "notification_events",
    #             "user.#"  # All user-targeted notifications
    #         )

    #         # Friend request events
    #         await self.rabbitmq.bind_queue(
    #             "friend_requests",
    #             "user_events",
    #             "friend_request.#"
    #         )

    #         #TODO: Do we want to keep this?
    #         # Status updates
    #         await self.rabbitmq.bind_queue(
    #             "status_notifications",
    #             "user_events",
    #             "status.#"  # Status change events
    #         )

    #         # Start consuming messages with appropriate handlers
    #         await self.rabbitmq.consume(
    #             "general_notifications",
    #             self._process_general_notification
    #         )
    #         await self.rabbitmq.consume(
    #             "user_notifications",
    #             self._process_user_notification
    #         )
    #         await self.rabbitmq.consume(
    #             "friend_requests",
    #             self._process_friend_request
    #         )
    #         await self.rabbitmq.consume(
    #             "status_notifications",
    #             self._process_status_notification
    #         )

    #         logger.info("Connected to RabbitMQ")
    #     except Exception as e:
    #         logger.error(f"Failed to connect to RabbitMQ: {e}")
    #         raise

    # async def _process_notification_message(self, message: Any) -> None:
    #     """Process a presence message from RabbitMQ."""
    #     # TODO: Get in sync with the team about how to use this

    #     try:
    #         body = json.loads(message.body.decode())
    #         message_type = body.get("type")

    #         if message_type == "status_update":
    #             user_id = body.get("user_id")
    #             status = body.get("status")
    #             last_changed = body.get("last_changed")

    #             if user_id and status:
    #                 if self.db_pool:  # Only handle DB operations in presence service
    #                     await with_retry(
    #                         lambda: self._save_user_status(
    #                             user_id, StatusType(status), last_changed),
    #                         max_attempts=3,
    #                         circuit_breaker=self.db_cb
    #                     )
    #                 else:  # Socket.IO service just updates in-memory state
    #                     self.presence_data[user_id] = {
    #                         "status": status,
    #                         "last_seen": last_changed or datetime.now().timestamp()
    #                     }

    #         elif message_type == "status_query":
    #             # Handle status queries through RabbitMQ
    #             if self.db_pool:
    #                 user_id = body.get("user_id")
    #                 status = await with_retry(
    #                     lambda: self._get_user_status(user_id),
    #                     max_attempts=3,
    #                     circuit_breaker=self.db_cb
    #                 )
    #                 # Publish status back
    #                 await with_retry(
    #                     lambda: self._publish_status_update(
    #                         user_id,
    #                         status.status if status else StatusType.OFFLINE
    #                     ),
    #                     max_attempts=3,
    #                     circuit_breaker=self.rabbitmq_cb
    #                 )

    #     except Exception as e:
    #         logger.error(f"Error processing presence message: {e}")
    #         await message.nack(requeue=False)
    #     else:
    #         await message.ack()

    async def get_user_notifications(self, user_id: str) -> List[NotificationResponse]:
        """Get user's notifications."""
        # Default values
        empty_notifications: List[NotificationResponse] = []

        # # Check cache first
        # if user_id in self.notification_data:
        #     notification_data = self.notification_data[user_id]
        #     return notification_data

        # Fetch from database if not in cache
        user_notifications = await self._get_user_notifications(user_id)
        if user_notifications:
            return user_notifications

        return empty_notifications
        
    async def _get_user_notifications(self, user_id: str) -> list[NotificationResponse] | None:
        """Get user notifications from database."""
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return None

        try:
            if isinstance(user_id, UUID):
                user_id = str(user_id)
            
            logger.debug(f"Searching for notifications with recipient_id: {user_id}")
            
            # Get the database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]
            
            stats = await db.command("collStats", "notifications") 
            logger.debug(f"Collection stats: {stats}")
            
            # Query for user notifications
            query = {"recipient_id": user_id}
            logger.debug(f"Query: {query}")
            cursor = db.notifications.find(query)
            documents = await cursor.to_list(length=None)  # Fetch all documents into a list
            logger.debug(f"Found {len(documents)} notifications for user {user_id}")
            
            notifications = []
            for doc in documents:
                logger.debug(f"Processing document: {doc}")
                # Convert MongoDB doc to database model
                db_notification = NotificationDB.from_mongo_doc(doc)
                
                # Convert database model to API response
                api_notification = db_notification.to_api_response()
                                
                notifications.append(api_notification)
                
            return notifications 

        except ValueError as e:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return None

    async def create_notification(self, notification: NotificationRequest) -> List[NotificationResponse]:
        """Create a new notification."""
        if not self.mongo_client:
            logger.warning("MongoDB not available")
            return []

        try:
            # Convert API request to database model
            db_notification = notification.to_db_model()
            
            # Get database
            db_name = self.config["mongodb"].get("database", "notifications")
            db = self.mongo_client[db_name]
            
            # Convert to MongoDB document and insert
            mongo_dict = db_notification.to_mongo_dict()
            result = await db.notifications.insert_one(mongo_dict)
            logger.info(f"Notification inserted with ID: {result.inserted_id}")
            
            # Return all notifications for the recipient
            return await self.get_user_notifications(notification.recipient_id)
            
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return []

    def set_user_notification(self, user_id: str, user_notification: NotificationRequest) -> bool:
        """Set user's notifications."""
        try:
            notification_type = NotificationType(
                user_notification.notification_type)
            current_time = user_notification.timestamp or datetime.now().timestamp()

            # Initialize user in presence_data if not exists
            if user_id not in self.notification_data:
                self.notification_data[user_id] = NotificationRequest(
                    notification_id=user_notification.notification_id,
                    recipient_id=user_notification.recipient_id,
                    sender_id=user_notification.sender_id,
                    reference_id=user_notification.reference_id,
                    content_preview=user_notification.content_preview,
                    timestamp=current_time,
                    notification_type=notification_type.value,
                    read=user_notification.read
                )
                logger.info(
                    f"Created new notification entry for user {user_id}")

            else:
                self.notification_data[user_id].update(NotificationRequest(
                    notification_id=user_notification.notification_id,
                    recipient_id=user_notification.recipient_id,
                    sender_id=user_notification.sender_id,
                    reference_id=user_notification.reference_id,
                    content_preview=user_notification.content_preview,
                    timestamp=current_time,
                    notification_type=notification_type.value,
                    read=user_notification.read
                ))

            # Update status in database and notify others with circuit breaker
            # await with_retry(
            #     lambda: self._update_user_status(user_id, status_type),
            #     max_attempts=3,
            #     circuit_breaker=self.db_cb
            # )

            logger.info(
                f"Added {notification_type} notification to User {user_id}")
            return True
        except ValueError as e:
            logger.error(
                f"Invalid notification type: {user_notification.notification_type}. Exception: {e}")
            return False

    # async def _update_user_notification(
    #     self,
    #     user_id: str,
    #     status: StatusType,
    #     last_changed: Optional[float] = None
    # ) -> bool:
    #     """Update a user's notifications.

    #     Returns:
    #         bool: True if update was successful, False otherwise
    #     """
    #     try:
    #         status_type = status
    #         current_time = last_changed or datetime.now().timestamp()

    #         # Initialize user in presence_data if not exists
    #         if user_id not in self.presence_data:
    #             self.presence_data[user_id] = {
    #                 "status": status_type.value,
    #                 "last_seen": current_time
    #             }
    #             logger.info(f"Created new presence entry for user {user_id}")

    #         else:
    #             self.presence_data[user_id].update({
    #                 "status": status_type.value,
    #                 "last_seen": last_changed or datetime.now().timestamp()
    #             })

    #         # Update status in database and notify others
    #         await with_retry(
    #             lambda: self._save_user_status(
    #                 user_id,
    #                 status_type,
    #                 last_changed
    #             ),
    #             max_attempts=3,
    #             circuit_breaker=self.db_cb
    #         )

    #         # Publish status update to RabbitMQ
    #         await with_retry(
    #             lambda: self._publish_status_update(
    #                 user_id,
    #                 status_type,
    #                 last_changed
    #             ),
    #             max_attempts=3,
    #             circuit_breaker=self.rabbitmq_cb
    #         )

    #         # Notify friends
    #         await with_retry(
    #             lambda: self._notify_friends(user_id, status_type),
    #             max_attempts=3,
    #             circuit_breaker=self.rabbitmq_cb
    #         )

    #         logger.info(f"User {user_id} status updated to {status}")
    #         return True

    #     except ValueError:
    #         logger.error(f"Invalid status: {status}")
    #         return False

    # async def _save_user_status(
    #     self,
    #     user_id: Union[str, int, UUID],
    #     status: StatusType,
    #     last_changed: Optional[float] = None
    # ) -> None:
    #     """Save user status to database.

    #     Args:
    #         user_id: User ID as string, int, or UUID
    #         status: User's status
    #         last_changed: Timestamp of last status change
    #     """
    #     if not self.db_pool:
    #         logger.warning("Database pool not available")
    #         return

    #     try:
    #         last_changed = last_changed or datetime.now().timestamp()

    #         # Handle different user_id types
    #         if isinstance(user_id, str):
    #             try:
    #                 # Try to parse as UUID first
    #                 uuid_user_id = UUID(user_id)
    #             except ValueError:
    #                 # If not a valid UUID string, generate a v4 UUID
    #                 uuid_user_id = UUID(int=int(user_id)) if user_id.isdigit() \
    #                     else UUID(bytes=user_id.encode(), version=4)
    #                 logger.debug(
    #                     f"Generated UUID v4 from string: {user_id} -> {uuid_user_id}"
    #                 )
    #         elif isinstance(user_id, int):
    #             # For integers, we create a UUID v4 using the int value
    #             # This maintains consistency for the same integer input
    #             try:
    #                 uuid_user_id = UUID(int=user_id)
    #             except ValueError:
    #                 # If integer is too large, fall back to random UUID
    #                 uuid_user_id = UUID(
    #                     bytes=str(user_id).encode(),
    #                     version=4
    #                 )
    #             logger.debug(
    #                 f"Generated UUID v4 from int: {user_id} -> {uuid_user_id}"
    #             )
    #         elif isinstance(user_id, UUID):
    #             uuid_user_id = user_id
    #         else:
    #             raise ValueError(f"Unsupported user_id type: {type(user_id)}")

    #         async with self.db_pool.acquire() as conn:
    #             await conn.execute(
    #                 """
    #                 INSERT INTO presence.user_status (
    #                     user_id,
    #                     status,
    #                     last_changed
    #                 ) VALUES ($1, $2, to_timestamp($3))
    #                 ON CONFLICT (user_id)
    #                 DO UPDATE SET
    #                     status = $2,
    #                     last_changed = to_timestamp($3)
    #                 """,
    #                 str(uuid_user_id),  # Convert UUID to string for PostgreSQL
    #                 status.value,
    #                 last_changed,
    #             )
    #     except Exception as e:
    #         logger.error(f"Failed to save user status: {e}")
    #         raise

    # async def _publish_status_update(
    #     self,
    #     user_id: str,
    #     status: StatusType,
    #     last_changed: Optional[float] = None
    # ) -> None:
    #     """Publish status update to RabbitMQ."""
    #     try:
    #         message = json.dumps({
    #             "user_id": user_id,
    #             "status": status.value,
    #             "last_changed": last_changed or datetime.now().timestamp(),
    #         })
    #         await self.rabbitmq.publish_message(
    #             exchange="user_events",
    #             routing_key=f"status.{user_id}",
    #             message=message
    #         )
    #     except Exception as e:
    #         logger.error(f"Failed to publish status update: {e}")
    #         raise

    # async def _notify_friends(self, user_id: str, status: StatusType) -> None:
    #     """Notify friends about a user's status change."""
    #     if not self.db_pool:
    #         logger.warning("Database pool not available")
    #         return

    #     try:
    #         # Get friends with circuit breaker
    #         friends = await with_retry(
    #             lambda: self._get_friends(user_id),
    #             max_attempts=3,
    #             circuit_breaker=self.db_cb
    #         )

    #         # Publish status update for each friend with circuit breaker
    #         for friend_id in friends:
    #             await with_retry(
    #                 lambda: self._publish_status_update(user_id, status),
    #                 max_attempts=3,
    #                 circuit_breaker=self.rabbitmq_cb
    #             )
    #     except Exception as e:
    #         logger.error(f"Failed to notify friends: {e}")
    #         raise

    # async def _get_friends(self, user_id: str) -> List[str]:
    #     """Get a user's friends."""
    #     if not self.db_pool:
    #         logger.warning("Database pool not available")
    #         return []

    #     try:
    #         async with self.db_pool.acquire() as conn:
    #             # Query for accepted connections in both directions
    #             query = """
    #                 SELECT connected_user_id FROM connections
    #                 WHERE user_id = $1 AND connection_status = 'accepted'
    #                 UNION
    #                 SELECT user_id FROM connections
    #                 WHERE connected_user_id = $1
    #                 AND connection_status = 'accepted'
    #             """
    #             rows = await conn.fetch(query, user_id)

    #             # Extract friend IDs from results
    #             friend_ids = []
    #             for row in rows:
    #                 friend_id = row["connected_user_id"] or row["user_id"]
    #                 friend_ids.append(friend_id)
    #             return friend_ids
    #     except Exception as e:
    #         logger.error(f"Failed to get friends: {e}")
    #         return []
