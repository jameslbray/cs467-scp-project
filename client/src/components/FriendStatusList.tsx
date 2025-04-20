import React from 'react';
import FriendStatusItem from './FriendStatusItem';
import { FriendStatus } from '../types.tsx';

interface FriendStatusListProps {
    statuses: Record<string, FriendStatus>;
  }

  const FriendStatusList: React.FC<FriendStatusListProps> = ({ statuses }) => {
    if (Object.keys(statuses).length === 0) {
      return <div>No friend statuses available.</div>; // Handle empty state
    }
  
    return (
      <div>
        <h2>Friend Statuses</h2>
        {Object.values(statuses).map((status) => ( // Use Object.values if key isn't needed here
          <FriendStatusItem key={status.user_id} status={status} />
        ))}
      </div>
    );
  };
  
  export default FriendStatusList;