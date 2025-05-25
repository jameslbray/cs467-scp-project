import type React from 'react';
import { useEffect, useState } from 'react';
import ChatList from '../components/ChatList';
import ConnectedUsers from '../components/ConnectedUsers';
import NotificationBell from '../components/NotificationsList';
import RoomList from '../components/RoomList';
import UserStatus from '../components/UserStatus';
import { useAuth } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import type { Room } from '../hooks/useFetchRooms';
import { useFetchRooms } from '../hooks/useFetchRooms';
import { ServerEvents } from '../types/serverEvents';
import type { UserStatusType } from '../types/userStatusType';
import type { NotificationResponseType } from "../types/notificationType"; // Add this import
import AddNotificationTest from '../components/AddNotificationTest';
import FriendsList from '../components/FriendsList';
import LoadingSpinner from '../components/LoadingSpinner';
import SearchUsers from '../components/SearchUsers';
import { useSocketEvent } from '../contexts/socket/useSocket';

const ChatPage: React.FC = () => {
    const { user, isLoading: authLoading } = useAuth();
    const { isConnected } = useSocketContext();
    const [friends, setFriends] = useState<Record<string, UserStatusType>>({});
    const [friendCount, setFriendCount] = useState(0);
    const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
    const { rooms, loading: roomsLoading } = useFetchRooms();
    // Add state for new notification indicator
    const [hasNewNotification, setHasNewNotification] = useState(false);

    // Listen for initial friend statuses
    useSocketEvent<{ statuses: Record<string, UserStatusType> }>(
        ServerEvents.FRIEND_STATUSES,
        (data) => {
            setFriends(data.statuses);
        }
    );

    // Listen for individual friend status changes
    useSocketEvent<UserStatusType>(ServerEvents.FRIEND_STATUS_CHANGED, (data) => {
        setFriends((prev) => ({ ...prev, [data.user_id]: data }));
    });

    // Listen for new notification events
    useSocketEvent<NotificationResponseType>(ServerEvents.NEW_NOTIFICATION, () => {
        setHasNewNotification(true);
        
        // Optional: Add sound notification
        try {
            const notificationSound = new Audio('/notification-sound.mp3');
            notificationSound.play().catch(e => console.log('Auto-play prevented:', e));
        } catch (e) {
            console.log('Audio notification not supported');
        }
    });

    // Reset notification indicator when the notification bell is clicked
    const handleNotificationBellClick = () => {
        setHasNewNotification(false);
    };

    // Update friend count when friends change
    useEffect(() => {
        setFriendCount(Object.keys(friends).length);
    }, [friends]);

    // Select 'general' room by default when rooms are loaded
    useEffect(() => {
        if (!roomsLoading && !selectedRoom && rooms.length > 0) {
            const generalRoom = rooms.find((room) => room.name.toLowerCase() === 'general');
            if (generalRoom) {
                setSelectedRoom(generalRoom);
            }
        }
    }, [rooms, roomsLoading, selectedRoom]);

    if (authLoading || !isConnected) {
        return <LoadingSpinner message='Connecting...' />;
    }

    if (!user) {
        return (
            <div className='flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900'>
                <div className='animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500' />
            </div>
        );
    }

    return (
        <div className='min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200'>
            {/* Header/Navigation */}
            <header className='bg-white dark:bg-gray-800 shadow-sm'>
                <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
                    <div className='flex justify-between items-center h-16'>
                        <div className='flex items-center'>
                            <UserStatus />
                        </div>
                        <div className='flex items-center space-x-4'>
                            {/* Notifications - now with hasNewNotification prop */}
                            <div className={hasNewNotification ? 'animate-pulse' : ''} onClick={handleNotificationBellClick}>
                                <NotificationBell />
                            </div>

                            {/* Rest of the header content remains the same */}
                            <SearchUsers
                                onConnectionChange={() => {
                                    // Refresh friend list when connections change
                                    // This could trigger a refetch if needed
                                }}
                            />

                            {/* Friend count */}
                            <FriendsList friends={friends} friendCount={friendCount} />
                        </div>
                    </div>
                </div>
            </header>

			{/* Main content */}
			<main className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
				<div className='grid grid-cols-1 lg:grid-cols-3 gap-8'>
					{/* Sidebar with status */}
					<div className='lg:col-span-1'>
						<RoomList onSelectRoom={setSelectedRoom} />
						<ConnectedUsers />
						<AddNotificationTest />
					</div>
					{/* Chat panel */}
					<div className='lg:col-span-2'>
						{selectedRoom ? (
							<ChatList roomId={selectedRoom._id} />
						) : (
							<div className='flex items-center justify-center h-full text-gray-500 dark:text-gray-400'>
								Select a room to start chatting
							</div>
						)}
					</div>
				</div>
			</main>
		</div>
	);
};

export default ChatPage;
