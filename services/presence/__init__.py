"""
Presence Service Package

This package provides functionality for tracking online presence of users
and notifying interested parties about presence changes.
"""

from services.presence.app.core.presence_manager import PresenceManager
# from services.socket_io.app.core.socket_server import SocketManager

# Use a function for lazy loading to break the circular import
def get_socket_manager():
    from services.socket_io.app.core.socket_server import SocketServer  # Or correct class name
    return SocketServer

__all__ = ["PresenceManager", "SocketManager"]
