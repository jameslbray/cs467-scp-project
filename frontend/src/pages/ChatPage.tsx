import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import AddNotificationTest from '../components/AddNotificationTest';
import ChatList from '../components/ChatList';
import ConnectedUsers from '../components/ConnectedUsers';
import FriendsList from '../components/FriendsList';
import LoadingSpinner from '../components/LoadingSpinner';
import NotificationBell from '../components/NotificationsList';
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
	// Add state for new notification indicator
	const [hasNewNotification, setHasNewNotification] = useState(false);
	const requestedFriendsRef = useRef(false);

	// Listen for individual friend status changes
	useSocketEvent<FriendConnection[]>(ServerEvents.GET_FRIENDS_SUCCESS, (data) => {
		console.log('Received friends list:', data);
		console.log('Type of data:', typeof data, 'Is array:', Array.isArray(data));
		setFriends((prev: Record<string, FriendConnection>) => {
			const updatedFriends: Record<string, FriendConnection> = { ...prev };

			// Check if data is an array
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
	useSocketEvent<NotificationResponseType>(ServerEvents.NEW_NOTIFICATION, (notification) => {
		setHasNewNotification(true);
		console.log('Received notification:', notification);

		// Optional: Add sound notification
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
				// Check if friends exist
				try {
					const enriched = await enrichConnectionsWithUsernames(friends, user.id);
					setEnrichedFriends(enriched);
				} catch (error) {
					console.error('Error enriching friends data:', error);
					// Don't clear existing data on error
				}
			} else if (user?.id && Object.keys(friends).length === 0) {
				// If friends is empty but user exists, set enrichedFriends to empty too
				setEnrichedFriends({});
			}
		};

		// Controller to handle component unmount during async operation
		const controller = new AbortController();
		enrich();
		return () => controller.abort();
	}, [friends, user?.id]);

	useEffect(() => {
		if (isConnected && user && socket && !requestedFriendsRef.current) {
			console.log('User before requesting friends:', user);
			console.log('Socket before requesting friends:', socket);
			console.log('Requesting friends list...');
			socket.emit(ServerEvents.GET_FRIENDS, { userId: user.id });
			requestedFriendsRef.current = true;
		}
		// Reset the flag if disconnected (optional, for reconnection scenarios)
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

	// Debugging: Log friends and enrichedFriends changes
	useEffect(() => {
		console.log('Friends changed:', Object.keys(friends).length);
	}, [friends]);

	useEffect(() => {
		console.log('Enriched friends changed:', Object.keys(enrichedFriends).length);
	}, [enrichedFriends]);

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
							<div
								className={hasNewNotification ? 'animate-pulse' : ''}
								onClick={handleNotificationBellClick}
							>
								<NotificationBell />
							</div>

							{/* Search users */}
							<SearchUsers
								onConnectionChange={() => {
									// Refresh friend list when connections change
									// This could trigger a refetch if needed
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
