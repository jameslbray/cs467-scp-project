// src/components/RoomList.tsx
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/solid';
import React, { useState } from 'react';
import { useAuth } from '../contexts';
import { useFriends } from '../contexts/friends/FriendsContext';
import { type Room, useFetchRooms } from '../hooks/useFetchRooms';
import { chatApi } from '../services/api';
import type { FriendConnection } from '../types/friendsTypes';

interface RoomListProps {
	onSelectRoom: (room: Room) => void;
	newChatButton?: boolean;
}

const RoomList: React.FC<RoomListProps> = ({ onSelectRoom, newChatButton }) => {
	const { rooms, loading, error } = useFetchRooms();
	const { user, token } = useAuth();
	const { acceptedFriends } = useFriends();
	const [showModal, setShowModal] = useState(false);
	const [friends, setFriends] = useState<FriendConnection[]>([]);
	const [selectedFriendIds, setSelectedFriendIds] = useState<string[]>([]);
	const [roomName, setRoomName] = useState('');
	const [creating, setCreating] = useState(false);
	const [createError, setCreateError] = useState<string | null>(null);
	const [activeRoomId, setActiveRoomId] = useState<string | null>(null);

	const openModal = async () => {
		if (!user?.id || !token) return;
		setFriends(Object.values(acceptedFriends));
		setShowModal(true);
	};

	const closeModal = () => {
		setShowModal(false);
		setSelectedFriendIds([]);
		setRoomName('');
		setCreateError(null);
	};

	const handleFriendToggle = (id: string) => {
		setSelectedFriendIds((prev) =>
			prev.includes(id) ? prev.filter((fid) => fid !== id) : [...prev, id]
		);
	};

	const handleCreateRoom = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!roomName.trim()) {
			setCreateError('Room name is required');
			return;
		}
		setCreating(true);
		setCreateError(null);
		try {
			await chatApi.createRoom({
				name: roomName,
				participant_ids: selectedFriendIds,
			});
			closeModal();
			window.location.reload(); // quick way to refresh room list
		} catch (err: unknown) {
			if (err instanceof Error) {
				setCreateError(err.message);
			} else {
				setCreateError('Failed to create room');
			}
		} finally {
			setCreating(false);
		}
	};

	const handleSelectRoom = (room: Room) => {
		setActiveRoomId(room._id);
		onSelectRoom(room);
	};

	if (loading) return <div>Loading rooms...</div>;
	if (error) return <div>Error: {error}</div>;

	return (
		<div className='bg-white dark:bg-gray-800 rounded-lg shadow-md p-4'>
			<button
				onClick={openModal}
				className='mb-4 w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition-colors'
			>
				<ChatBubbleLeftRightIcon className='h-5 w-5' />
				{newChatButton ? 'New Chat' : '+ Create Room'}
			</button>
			<ul className='divide-y divide-gray-200 dark:divide-gray-700'>
				{rooms.map((room) => (
					<li key={room._id}>
						<button
							type='button'
							onClick={() => handleSelectRoom(room)}
							className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors text-left
								${
									activeRoomId === room._id
										? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 font-bold shadow'
										: 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-100'
								}`}
							aria-current={activeRoomId === room._id ? 'true' : undefined}
						>
							<div className='flex items-center justify-center h-9 w-9 rounded-full bg-blue-500 text-white font-bold text-lg'>
								{room.name.charAt(0).toUpperCase()}
							</div>
							<span className='truncate text-base'>{room.name}</span>
						</button>
					</li>
				))}
			</ul>
			{showModal && (
				<div className='fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50'>
					<div className='bg-white p-6 rounded-lg shadow-lg w-80'>
						<h2 className='text-lg font-bold mb-2'>Create New Room</h2>
						<form onSubmit={handleCreateRoom}>
							<input
								type='text'
								placeholder='Room name'
								value={roomName}
								onChange={(e) => setRoomName(e.target.value)}
								className='w-full mb-2 px-2 py-1 border rounded-lg'
							/>
							<div className='mb-2'>
								<div className='font-semibold'>Add friends:</div>
								{friends.length === 0 ? (
									<div className='text-gray-500 text-sm'>No friends available</div>
								) : (
									<ul className='max-h-32 overflow-y-auto'>
										{friends.map((f) => {
											const friendId = f.user_id === user?.id ? f.friend_id : f.user_id;
											const friendName = f.userUsername || f.friendUsername || friendId;
											return (
												<li key={friendId}>
													<label className='flex items-center'>
														<input
															type='checkbox'
															checked={selectedFriendIds.includes(friendId)}
															onChange={() => handleFriendToggle(friendId)}
															className='mr-2 rounded-lg'
														/>
														<span>{friendName}</span>
													</label>
												</li>
											);
										})}
									</ul>
								)}
							</div>
							{createError && <div className='text-red-600 text-sm mb-2'>{createError}</div>}
							<div className='flex justify-end gap-2 mt-4'>
								<button
									type='button'
									onClick={closeModal}
									className='px-3 py-1 rounded-lg bg-gray-200'
								>
									Cancel
								</button>
								<button
									type='submit'
									className='px-3 py-1 rounded-lg bg-blue-600 text-white'
									disabled={creating}
								>
									{creating ? 'Creating...' : 'Create'}
								</button>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	);
};

export default RoomList;
