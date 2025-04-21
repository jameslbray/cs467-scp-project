from pydantic import BaseSettings, Field, PostgresDsn, AnyUrl


class Settings(BaseSettings):
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")

    # SQL Database (PostgreSQL) – e.g. for rooms, participants
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

    # MongoDB (message logs, analytics)
    MONGO_URI: AnyUrl = Field("mongodb://localhost:27017", env="MONGO_URI")
    MONGO_DB: str = Field("chat_db", env="MONGO_DB")

    # RabbitMQ (event bus)
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")
    CHAT_QUEUE: str = Field("chat_events", env="CHAT_QUEUE")

    # WebSocket / socket.io
    WS_HOST: str = Field("0.0.0.0", env="WS_HOST")
    WS_PORT: int = Field(8002, env="WS_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
