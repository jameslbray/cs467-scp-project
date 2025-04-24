import aio_pika
from .config import Settings


class RabbitMQClient:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.connection = None
        self.channel = None
        # aio-pika uses a connection string format
        self.connection_url = f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/{self.settings.RABBITMQ_VHOST}"

    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            # Connect using aio_pika's connect method
            self.connection = await aio_pika.connect_robust(self.connection_url)
            # Create a channel
            self.channel = await self.connection.channel()
            return True
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {str(e)}")
            return False

    async def close(self):
        """Close the RabbitMQ connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None

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
