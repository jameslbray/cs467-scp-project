from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Dict, List, Any


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application configuration
    APP_NAME: str = "Chat Service"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False)
    ENV: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    LOG_LEVEL: str = Field(default="info")

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="CORS allowed origins"
    )
    CORS_CREDENTIALS: bool = Field(
        default=True,
        description="Allow credentials"
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    CORS_HEADERS: List[str] = Field(
        default=["Authorization", "Content-Type"],
        description="Allowed HTTP headers"
    )

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
    PG_USER: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    PG_PASSWORD: str = Field(
        default="postgres",
        description="PostgreSQL password"
    )
    PG_HOST: str = Field(
        default="localhost",
        description="PostgreSQL host"
    )
    PG_DATABASE: str = Field(
        default="sycolibre",
        description="PostgreSQL database name"
    )
    PG_PORT: int = Field(
        default=5432,
        description="PostgreSQL port"
    )

    # Redis configuration
    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis host"
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="Redis port"
    )
    REDIS_PASSWORD: str = Field(
        default="",
        description="Redis password"
    )

    # RabbitMQ configuration
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL"
    )

    # Socket.IO server configuration
    SOCKET_PORT: int = Field(
        default=3001,
        description="Socket.IO server port"
    )
    SOCKET_HOST: str = Field(
        default="0.0.0.0",
        description="Socket.IO server host"
    )
    SOCKET_LOG_LEVEL: str = Field(
        default="info",
        description="Socket.IO log level"
    )

    # Socket.IO service URL
    SOCKET_IO_URL: str = Field(
        default="http://localhost:8000",
        description="URL of the Socket.IO service"
    )

    # Security settings
    SECRET_KEY: str = Field(
        default=...,
        description="Secret key for token signing",
        min_length=32
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Access token expiration time in minutes"
    )

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"ENV must be one of {allowed_envs}")
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug(cls, v: bool, info: Any) -> bool:
        if info.data.get("ENV") == "production" and v:
            raise ValueError("DEBUG cannot be True in production environment")
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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

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
    "settings",
    "get_pg_config",
    "get_redis_config",
    "get_rabbitmq_config",
    "get_presence_service_config",
]
