"""
Presence Service Package

This package provides functionality for tracking online presence of users
and notifying interested parties about presence changes.
"""

from .app.core.presence_manager import PresenceManager
from ..socket_io.app.core.socket_server import SocketServer

__all__ = ["PresenceManager", "SocketServer"]
