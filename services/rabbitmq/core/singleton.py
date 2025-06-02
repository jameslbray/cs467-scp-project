from .client import RabbitMQClient
from .config import Settings

_rabbitmq_client_instance = None


def get_rabbitmq_client():
    global _rabbitmq_client_instance
    if _rabbitmq_client_instance is None:
        _rabbitmq_client_instance = RabbitMQClient(Settings())
    return _rabbitmq_client_instance
