from pydantic import BaseSettings, Field, PostgresDsn


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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
