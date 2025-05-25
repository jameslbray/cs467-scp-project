import { FriendConnection } from '../types/friendsTypes';
import { userApi } from '../services/api';

const CONNECT_API_URL = 'http://localhost:8005';

export const fetchUserConnections = async (userId: string, token: string): Promise<FriendConnection[]> => {
  try {
    const response = await fetch(`${CONNECT_API_URL}/api/connect/${userId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch connections');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch user connections:', error);
    return [];
  }
};

export const fetchAcceptedFriends = async (userId: string, token: string): Promise<FriendConnection[]> => {
  try {
    const connections = await fetchUserConnections(userId, token);
    // Filter only accepted connections
    const acceptedConnections = connections.filter(
      (conn) => conn.status === 'accepted'
    );

    // Deduplicate connections - only keep one record per unique friend
    const uniqueFriends = new Map<string, FriendConnection>();

    acceptedConnections.forEach((conn) => {
      // Determine who the friend is (not the current user)
      const friendId = conn.user_id === userId ? conn.friend_id : conn.user_id;

      // Only keep one record per friend (preferring the one where current user is user_id)
      if (!uniqueFriends.has(friendId) || conn.user_id === userId) {
        uniqueFriends.set(friendId, conn);
      }
    });

    return Array.from(uniqueFriends.values());
  } catch (error) {
    console.error('Failed to fetch accepted friends:', error);
    return [];
  }
};

export const enrichConnectionsWithUsernames = async (
  connections: FriendConnection[], 
  currentUserId: string
): Promise<FriendConnection[]> => {
  try {
    // Deduplicate and extract unique friend IDs
    const friendIds = new Set<string>();
    const uniqueConnections = new Map<string, FriendConnection>();

    connections.forEach(conn => {
      const friendId = conn.user_id === currentUserId ? conn.friend_id : conn.user_id;

      // Only process each friend once
      if (!friendIds.has(friendId)) {
        friendIds.add(friendId);
        uniqueConnections.set(friendId, conn);
      }
    });

    // Get all user IDs for the API call (including current user for completeness)
    const allUserIds = new Set<string>();
    uniqueConnections.forEach(conn => {
      allUserIds.add(conn.user_id);
      allUserIds.add(conn.friend_id);
    });

    // Fetch users from user API
    const users = await userApi.getUsersByIds(Array.from(allUserIds));
    const userMap: Map<string, { id: string; username: string }> = new Map(
      (users as { id: string; username: string }[]).map(user => [user.id, user])
    );

    // Create enriched connections array
    return Array.from(uniqueConnections.values()).map(conn => {
      const enriched: FriendConnection = {
        ...conn,
        userUsername: userMap.get(conn.user_id)?.username,
        friendUsername: userMap.get(conn.friend_id)?.username
      };
      return enriched;
    });
  } catch (error) {
    console.error('Error enriching connections with usernames:', error);
    return connections; // Return original connections if enrichment fails
  }
};