import type React from 'react';
import { useEffect, useState } from 'react';
import type { UserStatusType } from '../types/userStatusType';
import ChatList from '../components/ChatList';
import ConnectedUsers from '../components/ConnectedUsers';
import RoomList from '../components/RoomList';
import UserStatus from '../components/UserStatus';
import { useAuth } from '../contexts';
import { useSocketEvent } from '../contexts/socket/useSocket';
import type { Room } from '../hooks/useFetchRooms';
import { useFetchRooms } from '../hooks/useFetchRooms';
import { ServerEvents } from '../types/serverEvents';
import NotificationBell from "../components/NotificationsList";
// import type { NotificationResponseType } from "../types/notificationType";
import AddNotificationTest from "../components/AddNotificationTest";
import FriendsList from '../components/FriendsList';
import SearchUsers from '../components/SearchUsers';

const ChatPage: React.FC = () => {
	const { user } = useAuth();
	const [friends, setFriends] = useState<Record<string, UserStatusType>>({});
	const [friendCount, setFriendCount] = useState(0);
	const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
	const { rooms, loading: roomsLoading } = useFetchRooms();

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
						<div className="flex items-center space-x-4">

							{/* Notifications */}
							<NotificationBell />

							{/* Search */}
							<SearchUsers onConnectionChange={() => {
								// Refresh friend list when connections change
								// This could trigger a refetch if needed
							}} />

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
