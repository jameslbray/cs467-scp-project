from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")

    # Database (PostgreSQL)
    DATABASE_URL: PostgresDsn = Field(
        ..., env="DATABASE_URL"
    )

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
    SECRET_KEY: str = "your-secret-key-here"  # Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


@lru_cache()
def get_settings():
    return Settings()
