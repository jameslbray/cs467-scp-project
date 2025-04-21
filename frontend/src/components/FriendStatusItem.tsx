import React from 'react';
import { FriendStatus } from '../types.tsx';

interface FriendStatusItemProps {
    status: FriendStatus;
}

const FriendStatusItem: React.FC<FriendStatusItemProps> = ({ status }) => {
    return (
        <div key={status.user_id}>
            {status.user_id}: {status.status}
        </div>
    );
};

export default FriendStatusItem;