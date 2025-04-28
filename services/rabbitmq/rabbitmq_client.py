# Re-export RabbitMQClient from core module for direct imports
from .core.client import RabbitMQClient

__all__ = ["RabbitMQClient"]
