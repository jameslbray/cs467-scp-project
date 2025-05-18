import os
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Socket.IO Service configuration settings"""

    # Service information
    PROJECT_NAME: str = "Socket.IO Service"
    VERSION: str = "0.1.0"

    # Environment
    ENV: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )

    # Socket.IO settings
    SOCKET_IO_PORT: int = int(os.getenv("SOCKET_IO_PORT", "8000"))
    SOCKET_IO_HOST: str = "0.0.0.0"
    SOCKET_IO_PATH: str = "/socket.io"
    SOCKET_IO_ASYNC_MODE: str = "asgi"
    SOCKET_IO_CORS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173",
        description="Socket.IO CORS allowed origins"
    )
    SOCKET_IO_PING_TIMEOUT: int = 5
    SOCKET_IO_PING_INTERVAL: int = 25
    SOCKET_IO_MAX_HTTP_BUFFER_SIZE: int = 1000000  # 1MB

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )

    # RabbitMQ settings
    RABBITMQ_HOST: str = Field(
        default="localhost", description="RabbitMQ host")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ port")
    RABBITMQ_USER: str = Field(
        default="guest", description="RabbitMQ username")
    RABBITMQ_PASSWORD: str = Field(
        default="guest", description="RabbitMQ password")
    RABBITMQ_VHOST: str = Field(
        default="/", description="RabbitMQ virtual host")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )


# Create a singleton instance
settings = Settings()


def get_socket_io_config() -> Dict[str, Any]:
    """Get Socket.IO server configuration."""
    return {
        "async_mode": settings.SOCKET_IO_ASYNC_MODE,
        "cors_allowed_origins": settings.SOCKET_IO_CORS_ALLOWED_ORIGINS,
        "ping_timeout": settings.SOCKET_IO_PING_TIMEOUT,
        "ping_interval": settings.SOCKET_IO_PING_INTERVAL,
        "max_http_buffer_size": settings.SOCKET_IO_MAX_HTTP_BUFFER_SIZE,
    }


def get_settings() -> Settings:
    return settings
