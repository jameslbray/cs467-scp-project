import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts';
// import { UserStatusType } from '../types/userStatusType';
import { FriendConnection } from '../types/friendsTypes';
// import { fetchAcceptedFriends, enrichConnectionsWithUsernames } from '../services/friendsAPI';
import { getFriendId, getFriendDisplayName, filterOnlineFriends } from '../utils/friendsUtils';
import { useFriendStatuses } from '../hooks/useFriendStatuses';

interface FriendsListProps {
  friends: Record<string, FriendConnection>;
}

const FriendsList: React.FC<FriendsListProps> = ({ friends }) => {
  const { user, token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'online' | 'all'>('online');
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const mounted = useRef<boolean>(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const {
    friendStatuses,
    fetchAllFriendStatuses,
    onlineFriendsCount
  } = useFriendStatuses(friends, user?.id, token, setLoading);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // // Load connections with usernames
  // async function loadConnectionsWithUsernames() {
  //   if (!user?.id || !token) return;

  //   setLoading(true);
  //   try {
  //     // Fetch accepted friends
  //     const connections = await fetchAcceptedFriends(user.id, token);

  //     // Enrich connections with usernames
  //     const enrichedConnections = await enrichConnectionsWithUsernames(connections, user.id);

  //     setAllFriends(enrichedConnections);
  //   } catch (error) {
  //     console.error('Error loading friends with usernames:', error);
  //   } finally {
  //     setLoading(false);
  //   }
  // }

  // Fetch friends when dropdown opens or tab changes
  useEffect(() => {
    // Only fetch on mount or when dependencies meaningfully change
    if (user?.id && (isOpen || Object.keys(friends).length > 0)) {
      setLoading(true);
      fetchAllFriendStatuses()
        .finally(() => {
          if (mounted.current) {
            setLoading(false);
          }
        });
    }
  }, [isOpen, user?.id, friends, fetchAllFriendStatuses]);

  // Render statuses on mount or when friends change
  useEffect(() => {
    if (user?.id) {
      fetchAllFriendStatuses();
    }
  }, [user?.id, friends]);

  return (
    <div className='relative' ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className='flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none'
        aria-expanded={isOpen}
      >
        <span className='mr-1'>
          {onlineFriendsCount} {onlineFriendsCount === 1 ? 'friend' : 'friends'} online
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
          fill='none'
          stroke='currentColor'
          viewBox='0 0 24 24'
          xmlns='http://www.w3.org/2000/svg'
        >
          <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M19 9l-7 7-7-7' />
        </svg>
      </button>

      {isOpen && (
        <div className='absolute right-0 mt-2 py-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700'>
          {/* Tabs */}
          <div className='flex border-b border-gray-200 dark:border-gray-700'>
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${activeTab === 'online'
                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              onClick={() => setActiveTab('online')}
            >
              Online ({onlineFriendsCount})
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${activeTab === 'all'
                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              onClick={() => setActiveTab('all')}
            >
              All Friends
            </button>
          </div>

          {/* Online Friends Tab */}
          {activeTab === 'online' && (
            <div className='max-h-60 overflow-y-auto'>
              {loading ? (
                <div className='py-4 px-4 text-center'>
                  <div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
                </div>
              ) : user?.id ? (
                renderFriendsList(filterOnlineFriends(friends, user.id, friendStatuses))
              ) : (
                <div className='px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic'>
                  No friends online
                </div>
              )}
            </div>
          )}

          {/* All Friends Tab */}
          {activeTab === 'all' && (
            <div className='max-h-60 overflow-y-auto'>
              {loading ? (
                <div className='py-4 px-4 text-center'>
                  <div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
                </div>
              ) : (
                renderFriendsList(friends)
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );

  // Helper function to render the friends list
  function renderFriendsList(connections: Record<string, FriendConnection>) {
    if (!user?.id) return null;

    if (Object.values(connections).length === 0) {
      return (
        <div className='px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic'>
          {activeTab === 'online' ? 'No friends online' : 'No friends found'}
        </div>
      );
    }

    return Object.values(connections).map((connection) => {
      const friendId = getFriendId(connection, user.id);
      const status = friendStatuses[friendId] || 'offline';
      const displayName = getFriendDisplayName(connection, friendId);

      return (
        <div
          key={connection.id}
          className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center'
        >
          <div
            className={`h-2 w-2 rounded-full mr-2 ${status === 'online'
              ? 'bg-green-500'
              : status === 'away'
                ? 'bg-yellow-500'
                : status === 'busy'
                  ? 'bg-red-500'
                  : 'bg-gray-500'
              }`}
          />
          <span className='truncate'>{displayName}</span>
          <span className='ml-auto text-xs text-gray-500 dark:text-gray-400'>
            {status}
          </span>
        </div>
      );
    });
  }
};

export default FriendsList;