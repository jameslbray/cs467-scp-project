import aio_pika
import json
import uuid
import asyncio
from typing import Dict, Any, Optional
from .config import Settings


class RabbitMQClient:
    def __init__(self, settings: Settings = Settings()):
        self.settings = settings or Settings()
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.futures: Dict[str, asyncio.Future] = {}
        # Use RABBITMQ_URL if provided, otherwise build from individual settings
        self.connection_url = (
            self.settings.RABBITMQ_URL
            if self.settings.RABBITMQ_URL
            else f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/{self.settings.RABBITMQ_VHOST}"
        )

    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            # Connect using aio_pika's connect method
            self.connection = await aio_pika.connect_robust(self.connection_url)
            # Create a channel
            self.channel = await self.connection.channel()

            # Set up RPC callback queue
            self.callback_queue = await self.channel.declare_queue(
                name='',  # Empty name means server will generate a unique name
                exclusive=True,  # Only this connection can use the queue
                auto_delete=True  # Queue will be deleted when connection closes
            )

            # Start consuming responses
            await self.callback_queue.consume(self._on_response)

            return True
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {str(e)}")
            return False

    async def _on_response(self, message: aio_pika.IncomingMessage):
        """Handle RPC responses"""
        async with message.process():
            if message.correlation_id is None:
                return

            future = self.futures.get(message.correlation_id)
            if future is not None:
                future.set_result(json.loads(message.body.decode()))
                del self.futures[message.correlation_id]

    async def publish_and_wait(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        correlation_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Publish a message and wait for response"""
        if not self.is_connected():
            await self.connect()

        # Generate correlation ID if not provided
        correlation_id = correlation_id or str(uuid.uuid4())

        # Create future for response
        future = asyncio.Future()
        self.futures[correlation_id] = future

        # Create message
        message_body = aio_pika.Message(
            body=json.dumps(message).encode(),
            correlation_id=correlation_id,
            reply_to=self.callback_queue.name,
        )

        # Publish message
        if exchange:
            exchange_obj = await self.channel.get_exchange(exchange, ensure=False)
            await exchange_obj.publish(message_body, routing_key=routing_key)
        else:
            await self.channel.default_exchange.publish(
                message_body, routing_key=routing_key
            )

        try:
            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            del self.futures[correlation_id]
            raise TimeoutError(f"Request timed out after {timeout} seconds")

    async def close(self):
        """Close the RabbitMQ connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.callback_queue = None
            self.futures.clear()

    def is_connected(self):
        """Check if connected to RabbitMQ"""
        return self.connection is not None and not self.connection.is_closed

    async def publish_message(self, exchange: str, routing_key: str, message: str):
        """Publish a message to a specific exchange with routing key"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Create a message with the string body
        message_body = aio_pika.Message(body=message.encode("utf-8"))

        # Publish the message
        if exchange:
            # Get the exchange by name or declare it if it doesn't exist
            exchange_obj = await self.channel.get_exchange(exchange, ensure=False)
            # Publish to the named exchange
            await exchange_obj.publish(message_body, routing_key=routing_key)
        else:
            # Use default exchange if no exchange name is provided
            await self.channel.default_exchange.publish(
                message_body, routing_key=routing_key
            )

    async def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Declare the queue using aio_pika
        await self.channel.declare_queue(name=queue_name, durable=durable)

    async def declare_exchange(self, exchange_name: str, exchange_type: str = "direct"):
        """Declare an exchange"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Map exchange type strings to aio_pika ExchangeType enum
        exchange_type_map = {
            "direct": aio_pika.ExchangeType.DIRECT,
            "fanout": aio_pika.ExchangeType.FANOUT,
            "topic": aio_pika.ExchangeType.TOPIC,
            "headers": aio_pika.ExchangeType.HEADERS,
        }

        # Get the exchange type or default to DIRECT
        exchange_type_enum = exchange_type_map.get(
            exchange_type.lower(), aio_pika.ExchangeType.DIRECT
        )

        # Declare the exchange
        await self.channel.declare_exchange(
            name=exchange_name, type=exchange_type_enum, durable=True
        )

    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str):
        """Bind a queue to an exchange with a routing key"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Get the queue
        queue = await self.channel.get_queue(queue_name)

        # Get the exchange
        exchange = await self.channel.get_exchange(exchange_name)

        # Bind the queue to the exchange with the routing key
        await queue.bind(exchange=exchange, routing_key=routing_key)

    async def consume(self, queue_name: str, callback):
        """Start consuming messages from a queue"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        # Get the queue
        queue = await self.channel.get_queue(queue_name)

        # Start consuming
        await queue.consume(callback)
