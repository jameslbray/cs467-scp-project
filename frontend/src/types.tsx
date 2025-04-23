// Status types from models.py
export enum StatusType {
  ONLINE = "online",
  AWAY = "away",
  OFFLINE = "offline"
}

export interface FriendStatus {
  userId: string;
  status: StatusType;
  lastChanged: string;
}

// Client events (events sent from client to server)
export enum ClientEvents {
  UPDATE_STATUS = "presence_update_status",
  REQUEST_FRIEND_STATUSES = "presence_request_friend_statuses",
}

// Server events (events sent from server to clients)
export enum ServerEvents {
  STATUS_UPDATED = "presence_status_updated",
  FRIEND_STATUS_CHANGED = "presence_friend_status_changed",
  FRIEND_STATUSES = "presence_friend_statuses",
  ERROR = "presence_error"
}

// User status interface from models.py
export interface UserStatus {
  userId: string;
  status: StatusType;
  lastChanged: string;
}

// Socket response interfaces
export interface FriendStatusesResponse {
  statuses: Record<string, UserStatus>;
}

export interface StatusUpdateResponse {
  message: string;
  status: StatusType;
}

export interface ErrorResponse {
  message: string;
}

export interface User {
  userId: string;
  username: string;
  profile_picture_url: string | null;
}