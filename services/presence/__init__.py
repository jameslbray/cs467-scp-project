"""
Presence Service Package

This package provides functionality for tracking online presence of users
and notifying interested parties about presence changes.
"""

from .manager import PresenceManager
from .websocket import SocketManager

__all__ = ["PresenceManager", "SocketManager"]
