import React from 'react';
import { v4 as uuidv4 } from 'uuid';
import { createNotification } from '../services/notificationsAPI.ts';
import { useAuth } from '../contexts/auth/authContext.ts';

const AddNotificationTest: React.FC = () => {

    const { user } = useAuth();
    if (!user) {
        return <div>Please log in to send notifications.</div>;
    }
    const senderId: string = uuidv4();
    const roomId: string = uuidv4();

    const handleClick = async () => {
        await createNotification(
            user.id, // User ID
            senderId, // Sender ID
            roomId, // Reference ID
            'Hello World!',  // Content preview
            'message'  // Notification type
        );
    };

    return (
        <button
            style={{
                backgroundColor: 'red',
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '4px',
                cursor: 'pointer',
            }}
            onClick={handleClick}
        >
            Send Notification
        </button>
    );
};

export default AddNotificationTest;