import React from 'react';
import { StatusType } from '../types.tsx'; // ServerEvents, UserStatus, ClientEvents
// import { useAuth } from '../contexts/auth/index.tsx';
import { useUserStatus } from '../hooks/useUserStatus.ts';


const UserStatus: React.FC = () => {
  // const { user } = useAuth();
  const { status, isLoading, error, updateStatus } = useUserStatus(); // message

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const newStatus = e.target.value as StatusType;
    updateStatus(newStatus);
  };

  return (
    <div className="flex items-center">
      <div
        className={`h-2 w-2 rounded-full mr-2 ${status === 'online' ? 'bg-green-500' :
          status === 'away' ? 'bg-yellow-500' :
            ' text-gray-500'
          }`}
      ></div>
      <span className="text-sm text-gray-700 dark:text-gray-300 mr-2">
        Status:
      </span>
      {isLoading ? (
        <span className="text-sm text-gray-700 dark:text-gray-300 animate-pulse">Loading...</span>
      ) : error ? (
        <span className="text-sm text-red-500">{error}</span>
      ) : (
          <select
            id="status-select"
            value={status}
            onChange={handleStatusChange}
            className="text-sm text-gray-700 dark:text-gray-300 bg-transparent appearance-none focus:outline-none cursor-pointer p-2"
            aria-label="User status"
          >
            <option value="online">Online</option>
            <option value="away">Away</option>
            <option value="offline">Offline</option>
          </select>
      )
      }
    </div>
  );
};

export default UserStatus;