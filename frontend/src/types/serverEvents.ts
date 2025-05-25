export enum ServerEvents {
  PRESENCE_UPDATE = 'presence',
  REQUEST_STATUSES = 'presence:request_friend_statuses',
  FRIEND_STATUSES = 'presence:friend_statuses',
  FRIEND_STATUS_CHANGED = 'presence:friend_status_changed',
  UPDATE_STATUS = 'presence:update_status',
  NEW_NOTIFICATION = "notification:new",
  NOTIFICATIONS_UPDATE = "notifications:update"
} 