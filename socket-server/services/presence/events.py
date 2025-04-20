from enum import Enum


class ClientEvents(str, Enum):
    """Events sent from clients to server"""
    UPDATE_STATUS = "presence:update_status"
    REQUEST_FRIEND_STATUSES = "presence:request_friend_statuses"


class ServerEvents(str, Enum):
    """Events sent from server to clients"""
    STATUS_UPDATED = "presence:status_updated"
    FRIEND_STATUS_CHANGED = "presence:friend_status_changed"
    FRIEND_STATUSES = "presence:friend_statuses"
    ERROR = "presence:error"
