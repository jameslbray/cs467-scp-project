// App.tsx
import React, { useEffect, useState, createContext, useContext } from 'react';
import { io, Socket } from 'socket.io-client';
import UserStatusDropdown from './components/UserStatusDropdown';
import ChatList from './components/ChatList';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';
// Define types for our context and props
export interface User {
  id: string;
  username: string;
  profilePicture?: string;
}

export interface UserStatus {
  user_id: string;
  status: 'online' | 'away' | 'offline';
  last_changed: string;
}

export enum ServerEvents {
  REQUEST_STATUSES = 'presence:request_friend_statuses',
  FRIEND_STATUSES = 'presence:friend_statuses',
  FRIEND_STATUS_CHANGED = 'presence:friend_status_changed',
  UPDATE_STATUS = 'presence:update_status'
}

// Dark mode context
type ThemeContextType = {
  darkMode: boolean;
  toggleDarkMode: () => void;
};

const ThemeContext = createContext<ThemeContextType>({
  darkMode: false,
  toggleDarkMode: () => {},
});

export const useTheme = () => useContext(ThemeContext);

const App: React.FC = () => {
  // State for user, socket, and friends
  const [socket, setSocket] = useState<Socket | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [friends, setFriends] = useState<Record<string, UserStatus>>({});
  const [isConnected, setIsConnected] = useState(false);
  
  // Dark mode state
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('darkMode') === 'true' ||
        window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  // Toggle dark mode function
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    if (typeof window !== 'undefined') {
      localStorage.setItem('darkMode', String(newDarkMode));
    }
  };

  // Apply dark mode class to html element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Fetch current user info (mocked for this example)
  useEffect(() => {
    // Simulating a logged-in user
    setCurrentUser({
      id: '1',
      username: 'michael_shaffer',
      profilePicture: 'https://i.pravatar.cc/150?u=1'
    });
  }, []);

  // Connect to socket server when user is authenticated
  useEffect(() => {
    if (!currentUser) return;

    // Initialize socket connection
    const socketConnection = io('http://localhost:3001');

    setSocket(socketConnection);

    // Connection events
    socketConnection.on('connect', () => {
      console.log('Connected to SycoLibre socket server');
      setIsConnected(true);

      // Request friend statuses after connection
      socketConnection.emit(ServerEvents.REQUEST_STATUSES, {});
    });

    socketConnection.on('disconnect', () => {
      console.log('Disconnected from SycoLibre socket server');
      setIsConnected(false);
    });

    // Handle friend status updates
    socketConnection.on(ServerEvents.FRIEND_STATUSES, (data: { statuses: Record<string, UserStatus> }) => {
      setFriends(data.statuses);
    });

    socketConnection.on(ServerEvents.FRIEND_STATUS_CHANGED, (data: UserStatus) => {
      setFriends(prev => ({
        ...prev,
        [data.user_id]: data
      }));
    });

    // Clean up connection on unmount
    return () => {
      socketConnection.disconnect();
    };
  }, [currentUser]);

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
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
    </ThemeContext.Provider>
  );
};
export default App;
