# Re-export RabbitMQClient from core module for direct imports
from services.rabbitmq.core.client import RabbitMQClient

__all__ = ['RabbitMQClient']
