import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import type React from 'react';
import { useEffect, useState } from 'react';
import type { UserStatusIntf } from '../App';
import ChatList from '../components/ChatList';
import ConnectedUsers from '../components/ConnectedUsers';
import NotificationBell from '../components/NotificationsList';
import RoomList from '../components/RoomList';
import UserStatus from '../components/UserStatus';
import { useAuth, useTheme } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useSocketEvent } from '../contexts/socket/useSocket';
import type { Room } from '../hooks/useFetchRooms';
import { useFetchRooms } from '../hooks/useFetchRooms';
import { ServerEvents } from '../types/serverEvents';
// import type { NotificationResponseType } from "../types/notificationType";
import AddNotificationTest from '../components/AddNotificationTest';
import LoadingSpinner from '../components/LoadingSpinner';

const ChatPage: React.FC = () => {
	const { darkMode, toggleDarkMode } = useTheme();
	const { user, logout, isLoading: authLoading } = useAuth();
	const { isConnected } = useSocketContext();
	const [friends, setFriends] = useState<Record<string, UserStatusIntf>>({});
	const [friendCount, setFriendCount] = useState(0);
	const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
	const { rooms, loading: roomsLoading } = useFetchRooms();

	// Listen for initial friend statuses
	useSocketEvent<{ statuses: Record<string, UserStatusIntf> }>(
		ServerEvents.FRIEND_STATUSES,
		(data) => {
			setFriends(data.statuses);
		}
	);

	// Listen for individual friend status changes
	useSocketEvent<UserStatusIntf>(ServerEvents.FRIEND_STATUS_CHANGED, (data) => {
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
							<NotificationBell />
							{/* Dark mode toggle */}
							<button
								type='button'
								onClick={toggleDarkMode}
								className='p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none'
								aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
							>
								{darkMode ? <SunIcon className='h-6 w-6' /> : <MoonIcon className='h-6 w-6' />}
							</button>

							{/* Connection status indicator */}
							<div className='flex items-center'>
								<div
									className={`h-2 w-2 rounded-full mr-2 ${
										isConnected ? 'bg-green-500' : 'bg-red-500'
									}`}
								/>
								<span className='text-sm text-gray-700 dark:text-gray-300'>
									{isConnected ? 'Connected' : 'Disconnected'}
								</span>
							</div>

							{/* Friend count */}
							<div className='text-sm text-gray-700 dark:text-gray-300'>
								{friendCount} {friendCount === 1 ? 'friend' : 'friends'} online
							</div>

							{/* Logout button */}
							<button
								type='button'
								onClick={logout}
								className='ml-4 px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none'
							>
								Logout
							</button>
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
