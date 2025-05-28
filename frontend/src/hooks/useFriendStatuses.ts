import { useState, useMemo } from 'react';
import { StatusAPI } from '../services/statusAPI';
import { FriendConnection } from '../types/friendsTypes';
import { getFriendId } from '../utils/friendsUtils';
import { useEffect, useCallback } from 'react';

export const useFriendStatuses = (
  friends: Record<string, FriendConnection>,
  currentUserId: string | undefined,
  token: string | null,
  setIsLoading: (loading: boolean) => void
) => {
  const [friendStatuses, setFriendStatuses] = useState<Record<string, string>>({});

  // Fetch all friend statuses
  const fetchAllFriendStatuses = useCallback(async () => {
    if (!currentUserId || !token || Object.keys(friends).length === 0) return;

    setIsLoading(true);
    try {
      const friendIds = Object.values(friends).map(conn =>
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
  }, [currentUserId, token, friends, setIsLoading]);

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


  useEffect(() => {
    let isMounted = true;

    if (Object.keys(friends).length > 0 && currentUserId) {
      const fetchStatuses = async () => {
        if (isMounted) {
          await fetchAllFriendStatuses();
        }
      };
      fetchStatuses();
    }

    return () => { isMounted = false; };
  }, [friends, currentUserId, token, fetchAllFriendStatuses]);

  return {
    friendStatuses,
    fetchAllFriendStatuses,
    getUserStatus,
    onlineFriendsCount
  };
};