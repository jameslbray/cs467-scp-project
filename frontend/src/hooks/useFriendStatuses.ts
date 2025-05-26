import { useState, useMemo } from 'react';
import { StatusAPI } from '../services/statusAPI';
import { FriendConnection } from '../types/friendsTypes';
import { getFriendId } from '../utils/friendsUtils';

export const useFriendStatuses = (
  friends: FriendConnection[],
  currentUserId: string | undefined,
  token: string | null
) => {
  const [friendStatuses, setFriendStatuses] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  // Fetch all friend statuses
  const fetchAllFriendStatuses = async () => {
    if (!currentUserId || !token || friends.length === 0) return;

    setIsLoading(true);
    try {
      const friendIds = friends.map(conn => 
        getFriendId(conn, currentUserId)
      );

      // Fetch status for each friend
      const statusPromises = friendIds.map(id =>
        StatusAPI.getUserStatus(id, token)
          .then(resp => ({ id, status: resp.status }))
          .catch(() => ({ id, status: 'offline' }))
      );

      const statuses = await Promise.all(statusPromises);

      // Update status state
      const newStatuses: Record<string, string> = {};
      statuses.forEach(item => {
        newStatuses[item.id] = item.status;
      });

      setFriendStatuses(newStatuses);
    } catch (error) {
      console.error('Failed to fetch friend statuses:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Get a specific user's status
  const getUserStatus = async (userId: string): Promise<string> => {
    // Return cached status if available
    if (friendStatuses[userId]) {
      return friendStatuses[userId];
    }

    // Call the Status API if we have a token
    if (token) {
      try {
        const statusResponse = await StatusAPI.getUserStatus(userId, token);
        // Update local state
        setFriendStatuses(prev => ({
          ...prev,
          [userId]: statusResponse.status
        }));
        return statusResponse.status;
      } catch (error) {
        console.error(`Failed to fetch status for user ${userId}:`, error);
        setFriendStatuses(prev => ({
          ...prev,
          [userId]: 'offline'
        }));
        return 'offline';
      }
    }
    
    return 'offline';
  };

  const onlineFriendsCount = useMemo(() => 
    Object.values(friendStatuses).filter(status => status === 'online').length, 
    [friendStatuses]
  );

  return {
    friendStatuses,
    isLoading,
    fetchAllFriendStatuses,
    getUserStatus,
    onlineFriendsCount
  };
};