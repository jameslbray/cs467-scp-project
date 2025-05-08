import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Socket.IO Service configuration settings."""

    # Service information
    PROJECT_NAME: str = "Socket.IO Service"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Environment
    ENV: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="CORS allowed origins"
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    CORS_HEADERS: List[str] = Field(
        default=["Authorization", "Content-Type"],
        description="Allowed HTTP headers"
    )

    # Socket.IO settings
    SOCKET_IO_PORT: int = int(os.getenv("SOCKET_IO_PORT", "8000"))
    SOCKET_IO_HOST: str = "0.0.0.0"
    SOCKET_IO_PATH: str = "/socket.io"
    SOCKET_IO_ASYNC_MODE: str = "asgi"
    SOCKET_IO_CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Socket.IO CORS allowed origins"
    )
    SOCKET_IO_PING_TIMEOUT: int = 5
    SOCKET_IO_PING_INTERVAL: int = 25
    SOCKET_IO_MAX_HTTP_BUFFER_SIZE: int = 1000000  # 1MB

    # Security settings
    JWT_SECRET_KEY: str = Field(
        default=...,
        description="JWT secret key for token signing"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )

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

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"ENV must be one of {allowed_envs}")
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info: Any) -> List[str]:
        if info.data.get("ENV") == "production":
            if "*" in v:
                raise ValueError(
                    "Wildcard CORS origin not allowed in production")
            if any(not origin.startswith("https://") for origin in v if origin != "null"):
                raise ValueError("Production CORS origins must use HTTPS")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long")
        return v

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
