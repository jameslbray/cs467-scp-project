from pydantic import BaseSettings, Field, PostgresDsn


class Settings(BaseSettings):
    # Environment
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")

    # Database (PostgreSQL)
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

    # JWT Auth
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"], env="CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
