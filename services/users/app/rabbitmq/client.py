import aio_pika


class Settings:
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"


class RabbitMQClient:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.connection = None
        self.channel = None
        self.connection_url = f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/{self.settings.RABBITMQ_VHOST}"

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            return True
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {str(e)}")
            return False

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None

    def is_connected(self):
        return self.connection is not None and not self.connection.is_closed

    async def publish_message(self, exchange: str, routing_key: str, message: str):
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        message_body = aio_pika.Message(body=message.encode("utf-8"))

        if exchange:
            exchange_obj = await self.channel.get_exchange(exchange, ensure=False)
            await exchange_obj.publish(message_body, routing_key=routing_key)
        else:
            await self.channel.default_exchange.publish(
                message_body, routing_key=routing_key
            )

    async def declare_queue(self, queue_name: str, durable: bool = True):
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        await self.channel.declare_queue(name=queue_name, durable=durable)

    async def declare_exchange(self, exchange_name: str, exchange_type: str = "direct"):
        if not self.is_connected():
            raise Exception("Not connected to RabbitMQ")

        exchange_type_map = {
            "direct": aio_pika.ExchangeType.DIRECT,
            "fanout": aio_pika.ExchangeType.FANOUT,
            "topic": aio_pika.ExchangeType.TOPIC,
            "headers": aio_pika.ExchangeType.HEADERS,
        }

        exchange_type_enum = exchange_type_map.get(
            exchange_type.lower(), aio_pika.ExchangeType.DIRECT
        )

        await self.channel.declare_exchange(
            name=exchange_name, type=exchange_type_enum, durable=True
        )

