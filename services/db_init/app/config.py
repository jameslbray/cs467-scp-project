import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


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


class Settings(BaseSettings):
    # Database connection
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: SecretStr = Field(default=SecretStr("postgres"))
    POSTGRES_HOST: str = Field(default="postgres_db")
    POSTGRES_PORT: str = Field(default="5432")
    POSTGRES_DB: str = Field(default="sycolibre")

    MONGO_USER: str = Field(default="admin")
    MONGO_PASSWORD: SecretStr = Field(default=SecretStr("password"))
    MONGO_HOST: str = Field(default="mongo_db")
    MONGO_PORT: str = Field(default="27017")
    MONGO_DB_NAME: str = Field(default="chat_db")

    MONGO_URI: str = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource=admin"

   # App user settings
    APP_USER: str = Field(default="app_user")
    APP_PASSWORD: SecretStr = Field(default=SecretStr("app_password"))

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def APP_DATABASE_URL(self) -> str:
        return f"postgresql://{self.APP_USER}:{self.APP_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

def get_settings() -> Settings:
    return Settings()
