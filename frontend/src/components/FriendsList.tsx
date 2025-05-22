import React, { useState, useRef, useEffect } from 'react';
import { UserStatusType } from '../types/userStatusType';
import { useAuth } from '../contexts';

interface FriendsListProps {
  friends: Record<string, UserStatusType>;
  friendCount: number;
}

const CONNECT_API_URL = 'http://localhost:8005';

const FriendsList: React.FC<FriendsListProps> = ({ friends, friendCount }) => {
  const { user, token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'online' | 'all'>('online');
  const [allFriends, setAllFriends] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // Fetch all friends when the "All" tab is selected
  useEffect(() => {
    if (isOpen && activeTab === 'all' && user?.id) {
      fetchAllFriends();
    }
  }, [isOpen, activeTab, user?.id]);

  const fetchAllFriends = async () => {
    if (!user?.id || !token) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect/${user.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const connections = await response.json();
        // Filter for accepted connections only
        const acceptedConnections = connections.filter(
          (conn: any) => conn.status === 'accepted'
        );
        setAllFriends(acceptedConnections);
      }
    } catch (error) {
      console.error('Failed to fetch all friends:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get the status of a user from the friends object
  const getUserStatus = (userId: string): string => {
    return friends[userId]?.status || 'offline';
  };

  // Get the username of a user from the friends object
  const getUserName = (userId: string): string => {
    return friends[userId]?.username || userId;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none"
        aria-expanded={isOpen}
      >
        <span className="mr-1">
          {friendCount} {friendCount === 1 ? 'friend' : 'friends'} online
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 py-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 dark:border-gray-700">
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${
                activeTab === 'online'
                  ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('online')}
            >
              Online ({friendCount})
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${
                activeTab === 'all'
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
            <div className="max-h-60 overflow-y-auto">
              {Object.keys(friends).length > 0 ? (
                Object.values(friends).map((friend) => (
                  <div 
                    key={friend.user_id} 
                    className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                  >
                    <div 
                      className={`h-2 w-2 rounded-full mr-2 ${
                        friend.status === 'online' ? 'bg-green-500' : 
                        friend.status === 'away' ? 'bg-yellow-500' : 'bg-gray-500'
                      }`} 
                    />
                    <span className="truncate">{friend.username || friend.user_id}</span>
                    <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">{friend.status}</span>
                  </div>
                ))
              ) : (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic">
                  No friends online
                </div>
              )}
            </div>
          )}

          {/* All Friends Tab */}
          {activeTab === 'all' && (
            <div className="max-h-60 overflow-y-auto">
              {loading ? (
                <div className="py-4 px-4 text-center">
                  <div className="animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full"></div>
                </div>
              ) : allFriends.length > 0 ? (
                allFriends.map((connection) => {
                  // Determine which ID is the friend (not the current user)
                  const friendId = connection.user_id === user?.id 
                    ? connection.friend_id 
                    : connection.user_id;
                  
                  const status = getUserStatus(friendId);
                  
                  return (
                    <div 
                      key={connection.id} 
                      className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                    >
                      <div 
                        className={`h-2 w-2 rounded-full mr-2 ${
                          status === 'online' ? 'bg-green-500' : 
                          status === 'away' ? 'bg-yellow-500' : 'bg-gray-500'
                        }`} 
                      />
                      <span className="truncate">{getUserName(friendId)}</span>
                      <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                        {status}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic">
                  No friends found
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FriendsList;