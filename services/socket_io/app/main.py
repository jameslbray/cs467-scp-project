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
socket_server = SocketServer()


class LifespanApp:
    """
    ASGI application wrapper that handles startup and shutdown events
    for initializing and cleaning up the SocketServer.
    """

    def __init__(self, app, socket_server: SocketServer):
        self.app = app
        self.socket_server = socket_server
        self._initialized = False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    if not self._initialized:
                        await self.socket_server.initialize()
                        self._initialized = True
                        logger.info(
                            "SocketServer initialized via ASGI lifespan event."
                        )
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    if self._initialized and hasattr(
                        self.socket_server, "shutdown"
                    ):
                        await self.socket_server.shutdown()
                        logger.info(
                            "SocketServer shutdown via ASGI lifespan event."
                        )
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            await self.app(scope, receive, send)


app = LifespanApp(socket_server.app, socket_server)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SOCKET_IO_HOST,
        port=settings.SOCKET_IO_PORT,
        reload=True,
    )
