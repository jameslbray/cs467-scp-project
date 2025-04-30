"""
Configuration settings for the presence service.
"""
from typing import List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, SecretStr


class Settings(BaseSettings):
    """Presence Service configuration settings."""

    # Service information
    PROJECT_NAME: str = "Presence Service"
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

    # Socket.IO settings
    SOCKET_IO_PORT: int = Field(
        default=8000,
        description="Socket.IO server port"
    )
    SOCKET_IO_HOST: str = Field(
        default="0.0.0.0",
        description="Socket.IO server host"
    )
    SOCKET_IO_PATH: str = Field(
        default="/socket.io",
        description="Socket.IO endpoint path"
    )
    SOCKET_IO_ASYNC_MODE: str = Field(
        default="asgi",
        description="Socket.IO async mode"
    )
    SOCKET_IO_CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Socket.IO CORS allowed origins"
    )
    SOCKET_IO_PING_TIMEOUT: int = Field(
        default=5,
        description="Socket.IO ping timeout in seconds"
    )
    SOCKET_IO_PING_INTERVAL: int = Field(
        default=25,
        description="Socket.IO ping interval in seconds"
    )
    SOCKET_IO_MAX_HTTP_BUFFER_SIZE: int = Field(
        default=1000000,
        description="Socket.IO max HTTP buffer size in bytes"
    )

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

    # Database settings
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_HOST: str = Field(default="localhost")
    # Note: Using 5433 as per docker-compose
    POSTGRES_PORT: str = Field(default="5433")
    POSTGRES_DB: str = Field(default="sycolibre")

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
        case_sensitive=True,
        extra="allow"
    )


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


def get_db_config() -> Dict[str, str]:
    """Return PostgreSQL configuration dictionary"""
    return {
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "database": settings.POSTGRES_DB,
    }
