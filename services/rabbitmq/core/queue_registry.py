"""
Centralized registry for all RabbitMQ queues in the system.
This module serves as the single source of truth for queue declarations.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .client import RabbitMQClient


@dataclass
class QueueConfig:
    """Configuration for a RabbitMQ queue"""

    name: str
    durable: bool = True
    auto_delete: bool = False
    arguments: Optional[Dict] = None
    exchange: Optional[str] = None
    routing_key: Optional[str] = None


class QueueRegistry:
    """Registry of all RabbitMQ queues in the system"""

    # Define all queues here
    QUEUES = {
        # Presence Service Queues
        "presence": QueueConfig(
            name="presence",
            durable=True,
            exchange="presence",
            routing_key="updates",
        ),
        # Chat Service Queues
        "chat_messages": QueueConfig(
            name="chat_messages",
            durable=True,
            exchange="chat",
            routing_key="messages",
        ),
        # Notification Service Queues
        "notifications": QueueConfig(
            name="notifications",
            durable=True,
            exchange="notifications",
            routing_key="all",
        ),
        # User Service Queues
        "user_events": QueueConfig(
            name="user_events",
            durable=True,
            exchange="users",
            routing_key="events",
        ),
        "connections": QueueConfig(
            name="connections",
            durable=True,
            exchange="connections",
            routing_key="events",
        ),
        # Notification Service Chat Listener
        "chat_notifications": QueueConfig(
            name="chat_notifications",
            durable=True,
            exchange="chat",
            routing_key="messages",
        ),
    }

    @classmethod
    async def setup_all(cls, client: RabbitMQClient):
        """
        Set up all queues and their bindings.

        Args:
            client: An initialized RabbitMQClient instance
        """
        # Ensure we're connected
        if not client.is_connected():
            await client.connect()

        # First declare all exchanges
        exchanges = {
            queue.exchange
            for queue in cls.QUEUES.values()
            if queue.exchange is not None
        }

        for exchange in exchanges:
            await client.declare_exchange(exchange)

        # Then declare all queues and their bindings
        for queue_config in cls.QUEUES.values():
            await client.declare_queue(
                queue_config.name,
                durable=queue_config.durable,
                auto_delete=queue_config.auto_delete,
                arguments=queue_config.arguments or {},
            )

            # If exchange and routing key are specified, create binding
            if queue_config.exchange and queue_config.routing_key:
                await client.bind_queue(
                    queue_config.name,
                    queue_config.exchange,
                    queue_config.routing_key,
                )

    @classmethod
    def get_queue_config(cls, queue_name: str) -> QueueConfig:
        """
        Get configuration for a specific queue.

        Args:
            queue_name: Name of the queue

        Returns:
            QueueConfig for the specified queue

        Raises:
            KeyError: If queue_name is not found in registry
        """
        return cls.QUEUES[queue_name]
