export type StatusValue = 'online' | 'away' | 'offline';

export interface FriendStatus {
  user_id: string;
  status: StatusValue;
  last_changed: string;
}

// Client events (events sent from client to server)
export enum ClientEvents {
  UPDATE_STATUS = "presence:update_status",
  REQUEST_FRIEND_STATUSES = "presence:request_friend_statuses"
}

// Server events (events sent from server to clients)
export enum ServerEvents {
  STATUS_UPDATED = "presence:status_updated",
  FRIEND_STATUS_CHANGED = "presence:friend_status_changed",
  FRIEND_STATUSES = "presence:friend_statuses",
  ERROR = "presence:error",
  REQUEST_STATUSES = 'presence:request_friend_statuses'
}

// Status types from models.py
export enum StatusType {
  ONLINE = "online",
  AWAY = "away",
  OFFLINE = "offline"
}

// User status interface from models.py
export interface UserStatus {
  user_id: string;
  status: StatusType;
  last_changed: string;
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
  id: string;
  username: string;
  profile_picture_url: string | null;
}