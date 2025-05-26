import { FriendConnection } from '../types/friendsTypes';
import { UserStatusType } from '../types/userStatusType';

export const getFriendId = (connection: FriendConnection, currentUserId: string): string => {
  return connection.user_id === currentUserId ? connection.friend_id : connection.user_id;
};

export const getFriendDisplayName = (
  connection: FriendConnection, 
  friendId: string,
  friends: Record<string, UserStatusType> = {}
): string => {
  // First check if we have the username from the enriched connection
  if (connection.user_id === friendId && connection.userUsername) {
    return connection.userUsername;
  }
  if (connection.friend_id === friendId && connection.friendUsername) {
    return connection.friendUsername;
  }

  // Fall back to the friends object
  if (friends[friendId]?.username) {
    return friends[friendId].username;
  }

  // Return the ID if no username is found
  return friendId;
};

export const filterOnlineFriends = (
  connections: FriendConnection[], 
  currentUserId: string,
  statuses: Record<string, string>
): FriendConnection[] => {
  return connections.filter(connection => {
    const friendId = getFriendId(connection, currentUserId);
    const status = statuses[friendId] || 'offline';
    return status === 'online';
  });
};