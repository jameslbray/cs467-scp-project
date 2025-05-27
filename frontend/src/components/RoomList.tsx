// src/components/RoomList.tsx
import React, { useState } from 'react';
import { useAuth } from '../contexts';
import { type Room, useFetchRooms } from '../hooks/useFetchRooms';
import { chatApi } from '../services/api';
import { fetchAcceptedFriends } from '../services/friendsAPI';
import type { FriendConnection } from '../types/friendsTypes';

interface RoomListProps {
	onSelectRoom: (room: Room) => void;
}

const RoomList: React.FC<RoomListProps> = ({ onSelectRoom }) => {
	const { rooms, loading, error } = useFetchRooms();
	const { user, token } = useAuth();
	const [showModal, setShowModal] = useState(false);
	const [friends, setFriends] = useState<FriendConnection[]>([]);
	const [selectedFriendIds, setSelectedFriendIds] = useState<string[]>([]);
	const [roomName, setRoomName] = useState('');
	const [creating, setCreating] = useState(false);
	const [createError, setCreateError] = useState<string | null>(null);

	const openModal = async () => {
		if (!user?.id || !token) return;
		const accepted = await fetchAcceptedFriends(user.id, token);
		setFriends(accepted);
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

	if (loading) return <div>Loading rooms...</div>;
	if (error) return <div>Error: {error}</div>;

	return (
		<div>
			<button
				onClick={openModal}
				className='mb-2 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700'
			>
				+ Create Room
			</button>
			<ul>
				{rooms.map((room) => (
					<li key={room._id}>
						<button type='button' onClick={() => onSelectRoom(room)}>
							{room.name}
						</button>
					</li>
				))}
			</ul>
			{showModal && (
				<div className='fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50'>
					<div className='bg-white p-6 rounded shadow-lg w-80'>
						<h2 className='text-lg font-bold mb-2'>Create New Room</h2>
						<form onSubmit={handleCreateRoom}>
							<input
								type='text'
								placeholder='Room name'
								value={roomName}
								onChange={(e) => setRoomName(e.target.value)}
								className='w-full mb-2 px-2 py-1 border rounded'
							/>
							<div className='mb-2'>
								<div className='font-semibold mb-1'>Add friends:</div>
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
															className='mr-2'
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
									className='px-3 py-1 rounded bg-gray-200'
								>
									Cancel
								</button>
								<button
									type='submit'
									className='px-3 py-1 rounded bg-blue-600 text-white'
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
