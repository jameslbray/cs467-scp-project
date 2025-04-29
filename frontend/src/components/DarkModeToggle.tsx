import React from 'react';
import { useTheme } from '../contexts';
import { useAuth } from '../contexts';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';

const DarkModeToggle: React.FC = () => {
  const { darkMode, toggleDarkMode } = useTheme();
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <button
      onClick={toggleDarkMode}
      className="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
      aria-label="Toggle dark mode"
    >
      {darkMode ? (
        <SunIcon className="h-6 w-6" />
      ) : (
        <MoonIcon className="h-6 w-6" />
      )}
    </button>
  );
};

export default DarkModeToggle;