export enum ServerEvents {
  PRESENCE_UPDATE = 'presence',
  FRIEND_STATUSES = 'presence:friend:statuses',
  FRIEND_STATUSES_SUCCESS = 'presence:friend:statuses:success',
  FRIEND_STATUSES_ERROR = 'presence:friend:statuses:error',
  FRIEND_STATUS_CHANGED = 'presence:friend:status:changed',
  UPDATE_STATUS = 'presence:update_status',
  NEW_NOTIFICATION = "notification:new",
  NOTIFICATIONS_UPDATE = "notifications:update",
  GET_FRIENDS = 'connections:get_friends',
  GET_FRIENDS_SUCCESS = 'connections:get_friends:success',
} 