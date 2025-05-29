import { BellIcon } from '@heroicons/react/24/outline';
import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import ChatList from '../components/ChatList';
import FriendsList from '../components/FriendsList';
import LoadingSpinner from '../components/LoadingSpinner';
import RoomList from '../components/RoomList';
import SearchUsers from '../components/SearchUsers';
import UserStatus from '../components/UserStatus';
import { useAuth } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useSocketEvent } from '../contexts/socket/useSocket';
import type { Room } from '../hooks/useFetchRooms';
import { useFetchRooms } from '../hooks/useFetchRooms';
import { enrichConnectionsWithUsernames } from '../services/friendsAPI';
import type { FriendConnection } from '../types/friendsTypes';
import type { NotificationResponseType } from '../types/notificationType';
import { ServerEvents } from '../types/serverEvents';
import { getFriendId } from '../utils/friendsUtils';

const ChatPage: React.FC = () => {
	const { user, isLoading: authLoading } = useAuth();
	const { isConnected, socket } = useSocketContext();
	const [friends, setFriends] = useState<Record<string, FriendConnection>>({});
	const [enrichedFriends, setEnrichedFriends] = useState<Record<string, FriendConnection>>({});
	const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
	const { rooms, loading: roomsLoading } = useFetchRooms();
	const [hasNewNotification, setHasNewNotification] = useState(false);
	const requestedFriendsRef = useRef(false);

	// Listen for individual friend status changes
	useSocketEvent<FriendConnection[]>(ServerEvents.GET_FRIENDS_SUCCESS, (data) => {
		setFriends((prev: Record<string, FriendConnection>) => {
			const updatedFriends: Record<string, FriendConnection> = { ...prev };
			if (Array.isArray(data)) {
				data.forEach((friend: FriendConnection) => {
					if (friend && friend.user_id) {
						if (user && user.id) {
							const friendId = getFriendId(friend, user.id);
							updatedFriends[friendId] = friend as FriendConnection;
						}
					}
				});
			}
			return updatedFriends;
		});
	});

	// Listen for new notification events
	useSocketEvent<NotificationResponseType>(ServerEvents.NEW_NOTIFICATION, () => {
		setHasNewNotification(true);
		try {
			const notificationSound = new Audio('../assets/notification-sound.mp3');
			notificationSound.play().catch((e) => console.log('Auto-play prevented:', e));
		} catch (e) {
			console.log('Audio notification not supported', e);
		}
	});

	// Reset notification indicator when the notification bell is clicked
	const handleNotificationBellClick = () => {
		setHasNewNotification(false);
	};

	// Update friend count when friends change
	useEffect(() => {
		const enrich = async () => {
			if (user?.id && Object.keys(friends).length > 0) {
				try {
					const enriched = await enrichConnectionsWithUsernames(friends, user.id);
					setEnrichedFriends(enriched);
				} catch (error) {
					console.error('Error enriching friends data:', error);
				}
			} else if (user?.id && Object.keys(friends).length === 0) {
				setEnrichedFriends({});
			}
		};
		const controller = new AbortController();
		enrich();
		return () => controller.abort();
	}, [friends, user?.id]);

	useEffect(() => {
		if (isConnected && user && socket && !requestedFriendsRef.current) {
			socket.emit(ServerEvents.GET_FRIENDS, { userId: user.id });
			requestedFriendsRef.current = true;
		}
		if (!isConnected) {
			requestedFriendsRef.current = false;
		}
	}, [isConnected, user, socket]);

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
							<UserStatus friends={Object.values(friends)} />
						</div>
						<div className='flex items-center space-x-4'>
							{/* Notifications */}
							<button
								className={`relative focus:outline-none ${
									hasNewNotification ? 'animate-pulse' : ''
								}`}
								onClick={handleNotificationBellClick}
								aria-label='Notifications'
								type='button'
							>
								<BellIcon className='h-6 w-6 text-gray-700 dark:text-gray-300' />
								{hasNewNotification && (
									<span className='absolute top-0 right-0 block h-2 w-2 rounded-full ring-2 ring-white dark:ring-gray-800 bg-red-500'></span>
								)}
							</button>
							{/* Search users */}
							<SearchUsers
								onConnectionChange={() => {
									// Refresh friend list when connections change
								}}
							/>
							{/* Friends List */}
							<FriendsList friends={enrichedFriends} />
						</div>
					</div>
				</div>
			</header>
			{/* Main content */}
			<main className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
				<div className='grid grid-cols-1 lg:grid-cols-3 gap-8 min-h-0'>
					{/* Sidebar with status */}
					<div className='lg:col-span-1'>
						<div className='rounded-lg shadow-md'>
							<RoomList onSelectRoom={setSelectedRoom} newChatButton />
						</div>
					</div>
					{/* Chat panel */}
					<div className='lg:col-span-2 min-h-0 flex flex-col'>
						<div className='bg-white dark:bg-gray-800 rounded-lg shadow-md h-full flex flex-col min-h-0'>
							{selectedRoom ? (
								<ChatList roomId={selectedRoom._id} />
							) : (
								<div className='flex items-center justify-center h-full text-gray-500 dark:text-gray-400'>
									Select a room to start chatting
								</div>
							)}
						</div>
					</div>
				</div>
			</main>
		</div>
	);
};

export default ChatPage;
