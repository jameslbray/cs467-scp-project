"""
Setup script for initializing RabbitMQ queues and exchanges.
"""

import asyncio
from core.client import RabbitMQClient
from core.config import Settings
from core.queue_registry import QueueRegistry


async def setup_rabbitmq():
    """Initialize all RabbitMQ queues and exchanges."""
    client = RabbitMQClient(Settings())

    try:
        # Connect to RabbitMQ
        await client.connect()

        # Set up all queues and exchanges
        await QueueRegistry.setup_all(client)

    finally:
        # Close the connection
        await client.close()


if __name__ == "__main__":
    asyncio.run(setup_rabbitmq())
