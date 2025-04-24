#!/usr/bin/env python3

import asyncio
import json
import sys
import logging
import aio_pika
import os

# Ensure proper path for imports
sys.path.insert(0, os.path.abspath("."))

# Import our RabbitMQ client
from services.users.app.core.rabbitmq import UserRabbitMQClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def consume_message(
    queue_name, connection_url, exchange_name=None, routing_key=None
):
    """
    Consume a single message from the specified queue to verify it was published.
    Returns the message body as a string.

    If exchange_name and routing_key are provided, ensures binding exists.
    """
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    # Get the queue
    queue = await channel.declare_queue(queue_name, passive=True)

    # If exchange and routing key are provided, ensure the binding exists
    if exchange_name and routing_key:
        # Get the exchange
        exchange = await channel.get_exchange(exchange_name)
        # Bind the queue to the exchange with the routing key
        await queue.bind(exchange, routing_key)
        logger.info(
            f"Ensured binding between queue '{queue_name}' and exchange '{exchange_name}' with key '{routing_key}'"
        )

    # Get a single message with a timeout of 5 seconds
    message = None
    try:
        # Use basic_get instead of consuming to just get one message
        message = await queue.get(timeout=5)
        if message:
            # Acknowledge the message
            await message.ack()
            # Convert body to string (it's bytes)
            body = message.body.decode("utf-8")
            logger.info(f"Received message: {body}")
            return body
    except Exception as e:
        logger.error(f"Error consuming message: {e}")
        return None
    finally:
        await connection.close()

    return None


async def bind_queue_to_exchange(
    connection_url, queue_name, exchange_name, routing_key
):
    """Utility function to bind a queue to an exchange with a routing key"""
    try:
        connection = await aio_pika.connect_robust(connection_url)
        channel = await connection.channel()

        # Get the queue
        queue = await channel.declare_queue(queue_name, passive=True)

        # Get the exchange
        exchange = await channel.get_exchange(exchange_name)

        # Bind the queue to the exchange with the routing key
        await queue.bind(exchange, routing_key)

        logger.info(
            f"Successfully bound queue '{queue_name}' to exchange '{exchange_name}' with routing key '{routing_key}'"
        )

        await connection.close()
        return True
    except Exception as e:
        logger.error(f"Failed to bind queue to exchange: {e}")
        return False


async def test_rabbitmq():
    """Test the RabbitMQ connection and message publishing"""
    client = UserRabbitMQClient()

    try:
        # Step 1: Initialize the client and connect
        logger.info("Initializing RabbitMQ client...")
        await client.initialize()
        logger.info("RabbitMQ client initialized successfully.")

        # Step 1.5: Bind the queue to the exchange
        connection_url = f"amqp://guest:guest@localhost:5672/"
        logger.info(
            f"Binding queue '{client.user_events_queue}' to exchange '{client.exchange_name}'..."
        )
        await bind_queue_to_exchange(
            connection_url,
            client.user_events_queue,
            client.exchange_name,
            client.user_events_queue,  # Using queue name as routing key
        )

        # Step 2: Define test data
        test_event_type = "user.test"
        test_user_data = {
            "id": "test-user-123",
            "name": "Test User",
            "email": "test@example.com",
            "timestamp": "2025-04-22T15:18:00Z",
        }

        # Step 3: Publish the test event
        logger.info(f"Publishing test event '{test_event_type}'...")
        await client.publish_user_event(test_event_type, test_user_data)
        logger.info("Test event published successfully.")

        # Step 4: Verify the message was published by consuming it
        # We need the connection URL to consume directly
        connection_url = f"amqp://guest:guest@localhost:5672/"
        connection_url = f"amqp://guest:guest@localhost:5672/"
        logger.info(f"Checking queue '{client.user_events_queue}' for messages...")

        # Pass exchange and routing key to ensure consistent message routing
        message_body = await consume_message(
            client.user_events_queue,
            connection_url,
            client.exchange_name,
            client.user_events_queue,  # Using queue name as routing key
        )
        # Step 5: Validate the received message
        if message_body:
            try:
                message_data = json.loads(message_body)
                assert (
                    message_data["event_type"] == test_event_type
                ), "Event type mismatch"
                assert (
                    message_data["user_data"]["id"] == test_user_data["id"]
                ), "User ID mismatch"
                logger.info(
                    "✅ Test successful! Message published and consumed correctly."
                )
            except (json.JSONDecodeError, AssertionError, KeyError) as e:
                logger.error(f"❌ Message validation failed: {e}")
        else:
            logger.error("❌ No message was received from the queue.")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        # Step 6: Clean up
        await client.close()
        logger.info("RabbitMQ client closed.")


if __name__ == "__main__":
    # Run the test
    logger.info("Starting RabbitMQ test...")
    asyncio.run(test_rabbitmq())
