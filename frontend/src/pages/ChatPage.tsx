import React, { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import UserStatusDropdown from '../components/UserStatusDropdown';
import ChatList from '../components/ChatList';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import { useTheme, useAuth } from '../contexts';
import { User, UserStatus } from '../App';
import { ServerEvents } from '../types/serverEvents';

// Custom hook for socket connection
const useSocketConnection = (currentUser: User | null) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [friends, setFriends] = useState<Record<string, UserStatus>>({});
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!currentUser) return;

    const socketConnection = io('http://localhost:3001', {
      auth: {
        token: localStorage.getItem('auth_token')
      }
    });
    setSocket(socketConnection);

    socketConnection.on('connect', () => {
      console.log('Connected to SycoLibre socket server');
      setIsConnected(true);
      socketConnection.emit(ServerEvents.REQUEST_STATUSES, {});
    });

    socketConnection.on('disconnect', () => {
      console.log('Disconnected from SycoLibre socket server');
      setIsConnected(false);
    });

    socketConnection.on(ServerEvents.FRIEND_STATUSES, (data: { statuses: Record<string, UserStatus> }) => {
      setFriends(data.statuses);
    });

    socketConnection.on(ServerEvents.FRIEND_STATUS_CHANGED, (data: UserStatus) => {
      setFriends(prev => ({
        ...prev,
        [data.user_id]: data
      }));
    });

    return () => {
      socketConnection.disconnect();
    };
  }, [currentUser]);

  return { socket, friends, isConnected };
};

const ChatPage: React.FC = () => {
  const { darkMode, toggleDarkMode } = useTheme();
  const { user, logout } = useAuth();
  const { friends, isConnected } = useSocketConnection(user);
  const [friendCount, setFriendCount] = useState(0);

  // Update friend count when friends change
  useEffect(() => {
    setFriendCount(Object.keys(friends).length);
  }, [friends]);

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200`}>
      {/* Header/Navigation */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">SycoLibre Chat</h1>
            </div>
            <div className="flex items-center space-x-4">
              {/* Dark mode toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none"
                aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? (
                  <SunIcon className="h-6 w-6" />
                ) : (
                  <MoonIcon className="h-6 w-6" />
                )}
              </button>
              
              {/* Connection status indicator */}
              <div className="flex items-center">
                <div className={`h-2 w-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {/* Friend count */}
              <div className="text-sm text-gray-700 dark:text-gray-300">
                {friendCount} {friendCount === 1 ? 'friend' : 'friends'} online
              </div>
              
              {/* Logout button */}
              <button
                onClick={logout}
                className="ml-4 px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Sidebar with status */}
          <div className="lg:col-span-1">
            <UserStatusDropdown />
          </div>

          {/* Chat panel */}
          <div className="lg:col-span-2">
            <ChatList />
          </div>
        </div>
      </main>
    </div>
  );
};

export default ChatPage; 