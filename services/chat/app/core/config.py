import os
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    """Find the .env file in potential locations."""
    # Check environment variable first
    env_file = os.getenv("ENV_FILE")
    if env_file and os.path.exists(env_file):
        return env_file

    # Try multiple possible locations
    possible_locations = [
        # Original path (for local development)
        os.path.join(Path(__file__).parent.parent.parent.parent, ".env"),
        # Docker container root
        "/app/.env",
        # Current directory
        ".env",
    ]

    for location in possible_locations:
        if os.path.exists(location):
            return location

    # If we get here, return the default location
    return possible_locations[0]

def construct_socket_path() -> str:

    host = os.getenv('SOCKET_IO_HOST', 'localhost')
    port = os.getenv('SOCKET_IO_PORT', '8000')
    path = os.getenv('SOCKET_IO_PATH', '/socket.io/')

    socket_io_url = f"https://{host}:{port}{path}"

    return socket_io_url

class Settings(BaseSettings):
    # Environment
    ENV: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode"
    )
    LOG_LEVEL: str = Field(
        default="info",
        description="Logging level"
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

    # Database settings
    DATABASE_URL: PostgresDsn = Field(
        default=...,
        description="Database connection URL"
    )
    POSTGRES_USER: str = Field(default=..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(default=..., min_length=8)
    POSTGRES_HOST: str = Field(default=..., min_length=1)
    POSTGRES_PORT: str = Field(default=..., min_length=1)
    POSTGRES_DB: str = Field(default=..., min_length=1)

    MONGO_USER: str = Field(default="admin")
    MONGO_PASSWORD: SecretStr = Field(default=SecretStr("password"))
    MONGO_HOST: str = Field(default="mongo_db")
    MONGO_PORT: str = Field(default="27017")
    MONGO_DB_NAME: str = Field(default="chat_db")

    MONGO_URI: str = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource=admin"

    # JWT settings
    JWT_SECRET_KEY: SecretStr = Field(default=..., min_length=32)
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Between 1 minute and 24 hours"
    )

    # RabbitMQ settings
    RABBITMQ_URL: str = Field(
        default=...,
        description="RabbitMQ connection URL"
    )
    RABBITMQ_HOST: str = Field(
        default="localhost",
        description="RabbitMQ host"
    )
    RABBITMQ_PORT: int = Field(
        default=5672,
        description="RabbitMQ port"
    )
    RABBITMQ_USER: str = Field(
        default="guest",
        description="RabbitMQ username"
    )
    RABBITMQ_PASSWORD: str = Field(
        default="guest",
        description="RabbitMQ password"
    )
    RABBITMQ_VHOST: str = Field(
        default="/",
        description="RabbitMQ virtual host"
    )
    USERS_QUEUE: str = Field(
        default="users_tasks",
        description="Users queue name"
    )

    SOCKET_IO_URL: str = construct_socket_path()

    # Security settings
    SECURITY_HEADERS: bool = Field(
        default=True,
        description="Enable security headers"
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        ge=1,
        description="Rate limit requests per period"
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=60,
        ge=1,
        description="Rate limit period in seconds"
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

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long")
        return v

    model_config = SettingsConfigDict(
            env_file=find_env_file(),
            env_file_encoding="utf-8",
            extra='ignore'
        )


@lru_cache()
def get_settings() -> Settings:
    """Create and return a cached Settings instance."""
    env_file = find_env_file()

    # Debug info
    print("\n================ CONFIG DEBUG ================")
    print(f"Looking for .env file at: {env_file}")
    print(f"File exists: {os.path.exists(env_file) if env_file else False}")

    # Create settings instance
    settings = Settings()

    # Print some key settings for debugging
    try:
        print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
        print(f"POSTGRES_HOST: {settings.POSTGRES_HOST}")
        print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
        print(f"ENV: {settings.ENV}")
    except Exception as e:
        print(f"Error accessing settings: {e}")

    print("===============================================\n")

    return settings
