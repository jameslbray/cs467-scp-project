"""
Main application module for the socket-io service.
"""

import logging
import os
import uvicorn
from dotenv import load_dotenv

from services.rabbitmq.core.config import Settings as RabbitMQSettings
from services.socket_io.app.core.socket_server import SocketServer
from .core.config import get_settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()
rabbitmq_settings = RabbitMQSettings(RABBITMQ_URL=os.getenv("RABBITMQ_URL"))

# Create socket server with RabbitMQ settings
socket_server = SocketServer(rabbitmq_settings)

# The ASGI app to serve
app = socket_server.app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SOCKET_IO_HOST,
        port=settings.SOCKET_IO_PORT,
        reload=True
    )
