"""
Configuration settings for the presence service.
"""

import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Presence Service configuration settings."""

    # Service information
    PROJECT_NAME: str = "Presence Service"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]

    # Socket.IO settings
    SOCKET_IO_PORT: int = 8000
    SOCKET_IO_HOST: str = "0.0.0.0"
    SOCKET_IO_PATH: str = "/socket.io"
    SOCKET_IO_ASYNC_MODE: str = "asgi"
    SOCKET_IO_CORS_ALLOWED_ORIGINS: List[str] = ["*"]
    SOCKET_IO_PING_TIMEOUT: int = 5
    SOCKET_IO_PING_INTERVAL: int = 25
    SOCKET_IO_MAX_HTTP_BUFFER_SIZE: int = 1000000  # 1MB

    # Security settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkey")
    JWT_ALGORITHM: str = "HS256"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


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
