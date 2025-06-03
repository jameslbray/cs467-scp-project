import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useSocketEvent } from '../contexts/socket/useSocket';
import { useFriendStatuses } from '../hooks/useFriendStatuses';
import { userApi } from '../services/api';
import { FriendConnection } from '../types/friendsTypes';
import type { User } from '../types/userType';
import { filterOnlineFriends, getFriendId } from '../utils/friendsUtils';

// interface FriendsListProps {
// 	friends: Record<string, FriendConnection>;
// }

const FriendsList: React.FC = () => {
	const { user, token } = useAuth();
	const [isOpen, setIsOpen] = useState(false);
	const [activeTab, setActiveTab] = useState<'online' | 'all'>('online');
	const [loading, setLoading] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const mounted = useRef<boolean>(true);
	const [userMap, setUserMap] = useState<Record<string, User>>({});
	const [friends, setFriends] = useState<Record<string, FriendConnection>>({});
	const { socket } = useSocketContext();

	// Listen for friend acceptance events
	useSocketEvent('connection:friend_accepted', () => {
		// Refresh the friends list
		fetchFriendsList();
	});

	// Function to fetch friends
	const fetchFriendsList = async () => {
		if (!socket || !user?.id) return;

		// Request updated friends list
		socket.emit('connections:get_friends', { user_id: user.id });
	};

	// Listen for the response with updated friends
	useSocketEvent('connections:get_friends:success', (data) => {
		if (data && Array.isArray(data)) {
			// Create a map using the friendId (not user_id) as key
			const friendsRecord: Record<string, FriendConnection> = {};

			data.forEach((friend: FriendConnection) => {
				if (!user?.id) return;

				// Get the actual friend's ID (not the current user's ID)
				const friendId = getFriendId(friend, user.id);

				if (!friendsRecord[friendId]) {
					friendsRecord[friendId] = friend;
				}
			});

			setFriends(friendsRecord);
		}
	});

	// Listen for any errors when fetching friends
	useSocketEvent('connections:get_friends:error', (error) => {
		console.error('Error fetching friends:', error);

		// Retry after a short delay
		setTimeout(() => {
			if (socket && user?.id) {
				console.log('Retrying friends list fetch...');
				socket.emit('connections:get_friends', { user_id: user.id });
			}
		}, 1000);
	});

	// Function to fetch and map user data
	const fetchUserData = async (userIds: string[]) => {
		if (!userIds.length) return;

		try {
			const users = await userApi.getUsersByIds(userIds);

			const newUserMap: Record<string, User> = {};
			users.forEach((user: User) => {
				newUserMap[user.id] = user;
			});

			setUserMap((prev) => ({ ...prev, ...newUserMap }));
		} catch (error) {
			console.error('Failed to fetch user details:', error);
		}
	};
	// Helper function to get display name from user ID
	const getUserDisplayName = (userId: string) => {
		if (userMap[userId]) {
			return (
				userMap[userId].username || userMap[userId].display_name || userId.substring(0, 8) + '...'
			);
		}
		return userId.substring(0, 8) + '...';
	};

	// Fetch user data when friends list changes
	useEffect(() => {
		if (friends && Object.keys(friends).length > 0 && user?.id) {
			// Convert from Record to array of friend IDs
			const friendIds = Object.values(friends).map((friend) => getFriendId(friend, user.id));

			// Filter out IDs we already have
			const idsToFetch = friendIds.filter((id) => !userMap[id]);

			if (idsToFetch.length > 0) {
				fetchUserData(idsToFetch);
			}
		}
	}, [friends, user?.id]);

	useEffect(() => {
		mounted.current = true;
		return () => {
			mounted.current = false;
		};
	}, []);

	// Use a hook to fetch friend statuses
	const { friendStatuses, fetchAllFriendStatuses, onlineFriendsCount } = useFriendStatuses(
		friends,
		user?.id,
		token,
		setLoading
	);

	// Close dropdown when clicking outside
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
				setIsOpen(false);
			}
		}
		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
		};
	}, []);

	// Fetch friend statuses when dropdown opens or friends change
	useEffect(() => {
		if (isOpen && user?.id) {
			fetchAllFriendStatuses();
		}
	}, [isOpen, user?.id, friends, fetchAllFriendStatuses]);

	useEffect(() => {
		if (socket && user?.id) {
			fetchFriendsList();
		}
	}, [socket, user?.id]);

	const isLoadingAnything = loading;

	return (
		<div className='relative' ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className='flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none'
				aria-expanded={isOpen}
			>
				<span className='mr-1'>
					{onlineFriendsCount} {onlineFriendsCount === 1 ? 'friend' : 'friends'} online
				</span>
				<svg
					className={`w-4 h-4 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
					fill='none'
					stroke='currentColor'
					viewBox='0 0 24 24'
					xmlns='http://www.w3.org/2000/svg'
				>
					<path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M19 9l-7 7-7-7' />
				</svg>
			</button>

			{isOpen && (
				<div className='absolute right-0 mt-2 py-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700'>
					{/* Tabs */}
					<div className='flex border-b border-gray-200 dark:border-gray-700'>
						<button
							className={`px-4 py-2 text-sm font-medium flex-1 ${
								activeTab === 'online'
									? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
							}`}
							onClick={() => setActiveTab('online')}
						>
							Online ({onlineFriendsCount})
						</button>
						<button
							className={`px-4 py-2 text-sm font-medium flex-1 ${
								activeTab === 'all'
									? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
							}`}
							onClick={() => setActiveTab('all')}
						>
							All Friends
						</button>
					</div>

					{/* Online Friends Tab */}
					{activeTab === 'online' && (
						<div className='max-h-60 overflow-y-auto'>
							{isLoadingAnything ? (
								<div className='py-4 px-4 text-center'>
									<div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
								</div>
							) : user?.id ? (
								renderFriendsList(filterOnlineFriends(friends, user.id, friendStatuses))
							) : (
								<div className='px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic'>
									No friends online
								</div>
							)}
						</div>
					)}

					{/* All Friends Tab */}
					{activeTab === 'all' && (
						<div className='max-h-60 overflow-y-auto'>
							{isLoadingAnything ? (
								<div className='py-4 px-4 text-center'>
									<div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
								</div>
							) : (
								renderFriendsList(friends)
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);

	// Helper function to render the friends list
	function renderFriendsList(connections: Record<string, FriendConnection>) {
		if (!user?.id) return null;
		const connectionList = Object.values(connections);
		if (connectionList.length === 0) {
			return (
				<div className='px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic'>
					{activeTab === 'online' ? 'No friends online' : 'No friends found'}
				</div>
			);
		}
		return connectionList.map((connection) => {
			const friendId = getFriendId(connection, user.id);
			const status = friendStatuses[friendId] || 'offline';
			const displayName = getUserDisplayName(friendId);

			return (
				<div
					key={friendId}
					className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center'
				>
					<div
						className={`h-2 w-2 rounded-full mr-2 ${
							status === 'online'
								? 'bg-green-500'
								: status === 'away'
								? 'bg-yellow-500'
								: status === 'busy'
								? 'bg-red-500'
								: 'bg-gray-500'
						}`}
					/>
					<span className='truncate'>{displayName}</span>
					<span className='ml-auto text-xs text-gray-500 dark:text-gray-400'>{status}</span>
				</div>
			);
		});
	}
};

export default FriendsList;
