import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts';
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';

interface User {
  id: string;
  username: string;
  profilePicture?: string;
}

interface Connection {
  id?: string;
  user_id: string;
  friend_id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'blocked';
}

interface SearchUsersProps {
  onConnectionChange?: () => void;
}

const CONNECT_API_URL = 'http://localhost:8005';
const USERS_API_URL = 'http://localhost:8001';

const SearchUsers: React.FC<SearchUsersProps> = ({ onConnectionChange }) => {
  const { user, token } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [pendingRequests, setPendingRequests] = useState<Connection[]>([]);
  const [userConnections, setUserConnections] = useState<Connection[]>([]);
  const [activeTab, setActiveTab] = useState<'search' | 'requests'>('search');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  // Get pending friend requests and user connections when component mounts
  useEffect(() => {
    if (user) {
      fetchUserConnections();
      fetchPendingRequests();
    }
  }, [user]);

  // Focus input when dropdown is opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Fetch user connections
  const fetchUserConnections = async () => {
    if (!user?.id || !token) return;
    
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect/all`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const connections = await response.json();
        setUserConnections(connections);
      }
    } catch (error) {
      console.error('Failed to fetch user connections:', error);
    }
  };

  // Fetch pending requests
  const fetchPendingRequests = async () => {
    if (!user?.id || !token) return;
    
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect/${user.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const connections = await response.json();
        // Filter for pending requests where this user is the recipient
        const pending = connections.filter((conn: Connection) => 
          conn.status === 'pending' && conn.friend_id === user.id
        );
        setPendingRequests(pending);
      }
    } catch (error) {
      console.error('Failed to fetch pending requests:', error);
    }
  };

  // Search for users
  const searchUsers = async () => {
    if (!searchTerm.trim() || !token) return;
    
    setIsLoading(true);
    try {
      // This endpoint would need to be implemented on your backend
      const response = await fetch(`${USERS_API_URL}/users/search?username=${encodeURIComponent(searchTerm)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const users = await response.json();
        // Filter out the current user
        setSearchResults(users.filter((u: User) => u.id !== user?.id));
      }
    } catch (error) {
      console.error('Failed to search users:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle search input changes
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    if (e.target.value.trim().length >= 2) {
      searchUsers();
    } else {
      setSearchResults([]);
    }
  };

  // Send a friend request
  const sendFriendRequest = async (friendId: string) => {
    if (!user?.id || !token) return;
    
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: user.id,
          friend_id: friendId,
          status: 'pending'
        })
      });
      
      if (response.ok) {
        // Refresh connections after sending request
        fetchUserConnections();
        if (onConnectionChange) onConnectionChange();
      }
    } catch (error) {
      console.error('Failed to send friend request:', error);
    }
  };

  // Accept a friend request
  const acceptRequest = async (connection: Connection) => {
    if (!user?.id || !token) return;
    
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: user.id,
          friend_id: connection.user_id,
          status: 'accepted'
        })
      });
      
      if (response.ok) {
        // Refresh requests and connections
        fetchPendingRequests();
        fetchUserConnections();
        if (onConnectionChange) onConnectionChange();
      }
    } catch (error) {
      console.error('Failed to accept friend request:', error);
    }
  };

  // Reject a friend request
  const rejectRequest = async (connection: Connection) => {
    if (!user?.id || !token) return;
    
    try {
      const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: user.id,
          friend_id: connection.user_id,
          status: 'rejected'
        })
      });
      
      if (response.ok) {
        // Refresh requests
        fetchPendingRequests();
        if (onConnectionChange) onConnectionChange();
      }
    } catch (error) {
      console.error('Failed to reject friend request:', error);
    }
  };

  // Get connection status between current user and another user
  const getConnectionStatus = (userId: string): string | null => {
    const connection = userConnections.find(
      conn => (conn.user_id === user?.id && conn.friend_id === userId) || 
              (conn.user_id === userId && conn.friend_id === user?.id)
    );
    
    return connection ? connection.status : null;
  };

  // Render connection button based on status
  const renderConnectionButton = (userId: string) => {
    const status = getConnectionStatus(userId);
    
    if (status === 'accepted') {
      return (
        <span className="text-green-500 text-xs">Connected</span>
      );
    } else if (status === 'pending') {
      return (
        <span className="text-yellow-500 text-xs">Pending</span>
      );
    } else if (status === 'rejected') {
      return (
        <span className="text-red-500 text-xs">Rejected</span>
      );
    } else if (status === 'blocked') {
      return null;
    } else {
      return (
        <button
          onClick={() => sendFriendRequest(userId)}
          className="text-xs bg-primary-500 hover:bg-primary-600 text-white px-2 py-1 rounded"
        >
          Connect
        </button>
      );
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none"
        aria-expanded={isOpen}
      >
        <MagnifyingGlassIcon className="h-5 w-5 mr-1" />
        <span>Find Friends</span>
        {pendingRequests.length > 0 && (
          <span className="ml-2 bg-red-500 text-white rounded-full h-5 w-5 flex items-center justify-center text-xs">
            {pendingRequests.length}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 py-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg z-20 border border-gray-200 dark:border-gray-700">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 dark:border-gray-700">
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${
                activeTab === 'search'
                  ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('search')}
            >
              Search
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium flex-1 ${
                activeTab === 'requests'
                  ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('requests')}
            >
              Requests {pendingRequests.length > 0 && `(${pendingRequests.length})`}
            </button>
          </div>

          {/* Search Tab */}
          {activeTab === 'search' && (
            <>
              <div className="px-4 py-2">
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={handleSearchChange}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  {searchTerm && (
                    <button
                      onClick={() => {
                        setSearchTerm('');
                        setSearchResults([]);
                      }}
                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              <div className="max-h-60 overflow-y-auto">
                {isLoading ? (
                  <div className="py-4 px-4 text-center">
                    <div className="animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full"></div>
                  </div>
                ) : searchResults.length > 0 ? (
                  searchResults.map((result) => (
                    <div
                      key={result.id}
                      className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between"
                    >
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 overflow-hidden mr-2">
                          {result.profilePicture ? (
                            <img src={result.profilePicture} alt={result.username} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-600 dark:text-gray-400">
                              {result.username.charAt(0).toUpperCase()}
                            </div>
                          )}
                        </div>
                        <span className="truncate font-medium">{result.username}</span>
                      </div>
                      {renderConnectionButton(result.id)}
                    </div>
                  ))
                ) : searchTerm ? (
                  <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center">
                    No users found
                  </div>
                ) : (
                  <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center">
                    Type at least 2 characters to search
                  </div>
                )}
              </div>
            </>
          )}

          {/* Requests Tab */}
          {activeTab === 'requests' && (
            <div className="max-h-60 overflow-y-auto">
              {pendingRequests.length > 0 ? (
                pendingRequests.map((request) => (
                  <div
                    key={request.id || `${request.user_id}-${request.friend_id}`}
                    className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 overflow-hidden mr-2">
                          <div className="w-full h-full flex items-center justify-center text-gray-600 dark:text-gray-400">
                            {request.user_id.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <span className="truncate font-medium">{request.user_id}</span>
                      </div>
                    </div>
                    <div className="flex space-x-2 mt-1">
                      <button
                        onClick={() => acceptRequest(request)}
                        className="flex-1 bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded text-xs"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => rejectRequest(request)}
                        className="flex-1 bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center">
                  No pending requests
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchUsers;