import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from .config import Settings


class RabbitMQClient:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.connection = None
        self.channel = None
        self.credentials = pika.PlainCredentials(
            self.settings.RABBITMQ_USER,
            self.settings.RABBITMQ_PASSWORD
        )
        self.parameters = pika.ConnectionParameters(
            host=self.settings.RABBITMQ_HOST,
            port=self.settings.RABBITMQ_PORT,
            virtual_host=self.settings.RABBITMQ_VHOST,
            credentials=self.credentials
        )

    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await AsyncioConnection.create(
                parameters=self.parameters
            )
            self.channel = await self.connection.channel()
            return True
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {str(e)}")
            return False

    async def close(self):
        """Close the RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    def is_connected(self):
        """Check if connected to RabbitMQ"""
        return self.connection is not None and not self.connection.is_closed

    async def publish_message(self, exchange: str, routing_key: str, message: str):
        """Publish a message to a specific exchange with routing key"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        await self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message
        )

    async def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        await self.channel.queue_declare(
            queue=queue_name,
            durable=durable
        )

    async def declare_exchange(self, exchange_name: str, exchange_type: str = 'direct'):
        """Declare an exchange"""
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        await self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )
