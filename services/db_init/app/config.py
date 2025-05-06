from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database connection
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: SecretStr = Field(default=SecretStr("postgres"))
    POSTGRES_HOST: str = Field(default="postgres_db")
    POSTGRES_PORT: str = Field(default="5432")
    POSTGRES_DB: str = Field(default="sycolibre")
    
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