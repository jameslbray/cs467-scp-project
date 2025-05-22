"""
Notification manager for handling user Connection state.
"""

import logging
import json
from uuid import UUID
from uuid import UUID
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import asyncpg  # type: ignore
# from pymongo import MongoClient

from services.shared.utils.retry import CircuitBreaker, with_retry
from services.shared.utils.retry import CircuitBreaker, with_retry
# from services.rabbitmq.core.client import RabbitMQClient
from ..db.models import (
    Connection,
)
from ..db.schemas import (
    Connection,
    ConnectionStatus,
    ConnectionCreate,
    ConnectionUpdate
)
    
# from services.socket_io.app.core.socket_server import SocketServer as SocketManager

# configure logging
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages user Connection state."""

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
        self.postgres_client: Optional[asyncpg.Pool] = None
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
            "postgres",
            failure_threshold=3,
            reset_timeout=30.0
        )

    async def initialize(self) -> None:
        """Initialize the Connections manager."""
        if self._initialized:
            logger.warning("Connection manager already initialized")
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

            # Initialize database connection with circuit breaker
            if "postgres" in self.config:
                await with_retry(
                    self._connect_database,
                    max_attempts=5,
                    initial_delay=5.0,
                    max_delay=60.0,
                    circuit_breaker=self.db_cb
                )

            self._initialized = True
            logger.info("Connection manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Connection manager: {e}")
            self._initialized = False  # Reset initialization flag on failure
            raise

    async def shutdown(self) -> None:
        """Shutdown the Connection manager."""
        # await self.rabbitmq.close()

        try:
            if self.postgres_client:
                await self.postgres_client.close()
                logger.info("Postgres connection closed")
        except Exception as e:
            logger.error(f"Error closing Postgres connection: {e}")
        finally:
            self.postgres_client = None
            logger.info("Connection manager shut down")

    async def _connect_database(self) -> None:
        """Connect to MongoDB."""
        # Connect to PostgreSQL
        config = self.config["postgres"].copy()

        try:
            # Connect to PostgreSQL
            if "options" in config:
                # Remove options as it's not supported by asyncpg
                del config["options"]

            self.postgres_client = await asyncpg.create_pool(
                min_size=2,
                max_size=10,
                **config
            )
            logger.info("Connected to PostgreSQL database")

            # Set search path for all connections in the pool
            async with self.postgres_client.acquire() as conn:
                await conn.execute('SET search_path TO connections, public')

                # Create schema and tables if they don't exist
                await conn.execute('CREATE SCHEMA IF NOT EXISTS connections')

                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS connections (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
                        friend_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
                        status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'rejected', 'blocked')),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT ck_user_friend_different CHECK (user_id != friend_id),
                        CONSTRAINT unique_connection UNIQUE (user_id, friend_id)
                    )
                    """
                )

                # Create proper indexes matching the SQLAlchemy model
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_connection_user ON connections (user_id)
                    """
                )
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_connection_friend ON connections (friend_id)
                    """
                )
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_connection_user_friend ON connections (user_id, friend_id)
                    """
                )

            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def check_connection_health(self):
        try:
            await self.postgres_client.execute("SELECT 1")
            return True
        except Exception:
            logger.error("Postgres connection failed")
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

    async def get_user_connections(self, user_id: str) -> List[Connection]:
        """Get a user's connections."""
        # Default values
        empty_connections: List[Connection] = []

        # Fetch from database if not in cache
        user_connections = await self._get_user_connections(user_id)
        if user_connections:
            return user_connections

        return empty_connections
        
    async def _get_user_connections(self, user_id: str) -> list[Connection] | None:
        """Get a user's connections from database."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:          
            logger.debug(f"Searching for connections of user_id: {user_id}")
            
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                
                await conn.execute('SET search_path TO connections, public')
                
                query = """
                    SELECT * FROM connections.connections
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                """
                # Execute the query
                rows = await conn.fetch(query, user_id)
                
                # Convert rows to list of Connection
                connections = []
                for row in rows:
                    try:
                        # Convert row to dict and handle UUID types
                        connection = Connection(
                            id=row['id'],
                            user_id=row['user_id'],
                            friend_id=row['friend_id'],
                            status=row['status'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        )
                        connections.append(connection)
                    except Exception as e:
                        logger.error(f"Error converting row to connection: {e}")
                    
                return connections

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user connections: {e}")
            return None

    async def get_all_connections(self) -> List[Connection]:
        """Get all connections."""
        # Default values
        empty_connections: List[Connection] = []

        # Fetch from database if not in cache
        user_connections = await self._get_all_connections()
        if user_connections:
            return user_connections

        return empty_connections
        
    async def _get_all_connections(self) -> list[Connection] | None:
        """Get all user connections from database."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:          
            logger.debug(f"Searching for all connections")            
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                
                await conn.execute('SET search_path TO connections, public')
                
                query = """
                    SELECT * FROM connections.connections
                """
                # Execute the query
                rows = await conn.fetch(query)
                
                # Convert rows to list of Connection
                connections = []
                for row in rows:
                    try:
                        # Convert row to dict and handle UUID types
                        connection = Connection(
                            id=row['id'],
                            user_id=row['user_id'],
                            friend_id=row['friend_id'],
                            status=row['status'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        )
                        connections.append(connection)
                    except Exception as e:
                        logger.error(f"Error converting row to connection: {e}")
                    
                return connections

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get user connections: {e}")
            return None

    async def create_connection(self, connection: ConnectionCreate) -> Connection | None:
        """Create a new connection."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:          
            logger.debug(f"Creating connection: {connection.user_id} -> {connection.friend_id}")
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                await conn.execute('SET search_path TO connections, public')
                
                # First direction (user_id -> friend_id)
                query1 = """
                    INSERT INTO connections.connections (user_id, friend_id, status)
                    VALUES ($1, $2, $3)
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                # Execute first query
                result1 = await conn.fetchrow(query1, connection.user_id, connection.friend_id, connection.status)
                
                # Second direction (friend_id -> user_id)
                query2 = """
                    INSERT INTO connections.connections (user_id, friend_id, status)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """
                # Execute second query
                result2 = await conn.fetchrow(query2, connection.friend_id, connection.user_id, connection.status)
                
                if result1 and result2:
                    logger.info(f"Bidirectional connection created with ID: {result1['id']}")
                    return Connection(
                        id=result1['id'],
                        user_id=result1['user_id'],
                        friend_id=result1['friend_id'],
                        status=result1['status'],
                        created_at=result1['created_at'],
                        updated_at=result1['updated_at']
                    )
                else:
                    logger.error("Failed to create connection")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

    async def update_connection(self, connection: ConnectionUpdate) -> Connection | None:
        """Update an existing connection."""
        if not self.postgres_client:
            logger.warning("Postgres not available")
            return None

        try:          
            logger.debug(f"Updating connection for {connection.user_id}")
            async with self.postgres_client.acquire() as conn:
                # Execute the query directly on the connection
                await conn.execute('SET search_path TO connections, public')
                
                query = """
                    UPDATE connections.connections
                    SET status = $1, updated_at = NOW()
                    WHERE (user_id = $2 AND friend_id = $3)
                    OR (user_id = $3 AND friend_id = $2)
                    RETURNING id, user_id, friend_id, status, created_at, updated_at
                """
                # Execute the query
                result = await conn.fetchrow(query, connection.status, connection.user_id, connection.friend_id)
                
                if result:
                    logger.info(f"Connection updated with ID: {connection.user_id}")
                    return Connection(
                        id=result['id'],
                        user_id=result['user_id'],
                        friend_id=result['friend_id'],
                        status=result['status'],
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                else:
                    logger.error("Failed to update connection")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to update connection: {e}")
            return None


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
