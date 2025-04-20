from enum import Enum


class ClientEvents(str, Enum):
    """Events sent from clients to server"""
    UPDATE_STATUS = "presence_update_status"
    REQUEST_FRIEND_STATUSES = "presence_:request_friend_statuses"


class ServerEvents(str, Enum):
    """Events sent from server to clients"""
    STATUS_UPDATED = "presence_status_updated"
    FRIEND_STATUS_CHANGED = "presence_friend_status_changed"
    FRIEND_STATUSES = "presence_friend_statuses"
    ERROR = "presence_error"
