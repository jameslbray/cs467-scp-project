from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path
from typing import List, Any


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
        env_file=os.getenv(
            "ENV_FILE",
            os.path.join(Path(__file__).parent.parent.parent.parent, ".env")
        ),
        env_file_encoding="utf-8",
        extra='ignore'
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
