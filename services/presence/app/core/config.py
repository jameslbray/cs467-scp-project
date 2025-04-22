import os
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Presence Service configuration settings."""
    
    # Service information
    PROJECT_NAME: str = "Presence Service"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Socket.IO client settings
    SOCKET_IO_URL: str = "http://socket-io:8000"  # URL of the socket-io service
    
    # Database settings - for future use
    DATABASE_URL: Optional[str] = None
    
    # Security settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkey")
    JWT_ALGORITHM: str = "HS256"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_socket_io_client_config() -> Dict[str, str]:
    """Get Socket.IO client configuration."""
    return {
        "url": settings.SOCKET_IO_URL,
    }

