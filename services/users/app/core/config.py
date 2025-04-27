from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    # Remove default to prevent accidental development mode
    ENV: str = Field(..., env="ENV")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")

    # Database (PostgreSQL)
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

    # RabbitMQ (for background tasks & notifications)
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")
    USERS_QUEUE: str = Field("users_tasks", env="USERS_QUEUE")

    # Database settings - using SecretStr for sensitive data
    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(..., min_length=8)
    POSTGRES_HOST: str = Field(..., min_length=1)
    POSTGRES_PORT: str = Field(..., min_length=1)
    POSTGRES_DB: str = Field(..., min_length=1)

    # JWT settings
    JWT_SECRET_KEY: SecretStr = Field(..., min_length=32)
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30, ge=1, le=1440)  # Between 1 minute and 24 hours

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    CORS_CREDENTIALS: bool = Field(default=True, env="CORS_CREDENTIALS")
    CORS_METHODS: List[str] = Field(default=["*"], env="CORS_METHODS")
    CORS_HEADERS: List[str] = Field(default=["*"], env="CORS_HEADERS")

    # Security headers
    SECURITY_HEADERS: bool = Field(default=True, env="SECURITY_HEADERS")
    RATE_LIMIT_REQUESTS: int = Field(
        default=100, ge=1, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(
        default=60, ge=1, env="RATE_LIMIT_PERIOD")  # in seconds

    # Environment-specific validations
    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v):
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"ENV must be one of {allowed_envs}")
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug(cls, v, info):
        if info.data.get("ENV") == "production" and v:
            raise ValueError("DEBUG cannot be True in production environment")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v):
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
def get_settings():
    return Settings()
