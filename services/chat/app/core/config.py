from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, List


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application configuration
    APP_NAME: str = "Chat Service"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False)
    ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="info")

    # MongoDB configuration
    MONGO_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string"
    )
    MONGO_DB: str = Field(
        default="chat_db",
        description="MongoDB database name"
    )

    # PostgreSQL configuration
    PG_USER: str = Field(default="postgres")
    PG_PASSWORD: str = Field(default="postgres")
    PG_HOST: str = Field(default="localhost")
    PG_DATABASE: str = Field(default="sycolibre")
    PG_PORT: int = Field(default=5432)

    # Redis configuration (commented out as in original)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="")

    # RabbitMQ configuration
    RABBITMQ_URL: str = Field(default="amqp://guest:guest@localhost:5672/")

    # Socket.IO server configuration
    SOCKET_PORT: int = Field(default=3001)
    SOCKET_HOST: str = Field(default="0.0.0.0")
    SOCKET_LOG_LEVEL: str = Field(default="info")

    # Socket.IO service URL
    SOCKET_IO_URL: str = Field(
        default="http://localhost:8000",
        description="URL of the Socket.IO service"
    )

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:5173", "*"])

    # Security
    SECRET_KEY: str = Field(default="chat_service_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Create settings instance
settings = Settings()

# Create configuration dictionaries for services


def get_pg_config() -> Dict[str, str]:
    """Return PostgreSQL configuration dictionary"""
    return {
        "user": settings.PG_USER,
        "password": settings.PG_PASSWORD,
        "host": settings.PG_HOST,
        "database": settings.PG_DATABASE,
        "port": settings.PG_PORT,
    }


def get_redis_config() -> Dict[str, str]:
    """Return Redis configuration dictionary"""
    return {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "password": settings.REDIS_PASSWORD,
    }


def get_rabbitmq_config() -> Dict[str, str]:
    """Return RabbitMQ configuration dictionary"""
    return {
        "url": settings.RABBITMQ_URL,
    }


def get_presence_service_config() -> Dict[str, Dict]:
    """Return full presence service configuration dictionary"""
    return {
        "postgres": get_pg_config(),
        # Redis is commented out as in original
        # "redis": get_redis_config(),
        "rabbitmq": get_rabbitmq_config(),
    }


# Export settings and config functions
__all__ = [
    'settings',
    'get_pg_config',
    'get_redis_config',
    'get_rabbitmq_config',
    'get_presence_service_config',
]
