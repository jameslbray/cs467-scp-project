from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")

    # Database (PostgreSQL)
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

    # RabbitMQ (for background tasks & notifications)
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")
    USERS_QUEUE: str = Field("users_tasks", env="USERS_QUEUE")

    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    # JWT settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    CORS_CREDENTIALS: bool = Field(default=True, env="CORS_CREDENTIALS")
    CORS_METHODS: List[str] = Field(default=["*"], env="CORS_METHODS")
    CORS_HEADERS: List[str] = Field(default=["*"], env="CORS_HEADERS")

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            Path(__file__).parent.parent.parent.parent, ".env"),
        env_file_encoding="utf-8",
        extra='allow'
    )


@lru_cache()
def get_settings():
    return Settings()
