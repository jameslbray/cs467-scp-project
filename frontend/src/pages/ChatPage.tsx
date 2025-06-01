import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import ChatList from '../components/ChatList';
import LoadingSpinner from '../components/LoadingSpinner';
import RoomList from '../components/RoomList';
import { useAuth } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import type { Room } from '../hooks/useFetchRooms';
import { useFetchRooms } from '../hooks/useFetchRooms';
import { ServerEvents } from '../types/serverEvents';

const ChatPage: React.FC = () => {
	const { user, isLoading: authLoading } = useAuth();
	const { isConnected, socket } = useSocketContext();
	const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
	const { rooms, loading: roomsLoading } = useFetchRooms();
	const requestedFriendsRef = useRef(false);

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
								<ChatList roomName={selectedRoom.name} roomId={selectedRoom._id} />
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
