import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts';
import { UserStatusType } from '../types/userStatusType';
import { userApi } from '../services/api';
import { StatusAPI } from '../services/statusAPI';

interface FriendConnection {
	id: string;
	user_id: string;
	friend_id: string;
	status: string;
	userUsername?: string | undefined;
	friendUsername?: string | undefined;
}

interface FriendsListProps {
	friends: Record<string, UserStatusType>;
	friendCount: number;
}

const CONNECT_API_URL = 'http://localhost:8005';

const FriendsList: React.FC<FriendsListProps> = ({ friends, friendCount }) => {
	const { user, token } = useAuth();
	const [isOpen, setIsOpen] = useState(false);
	const [activeTab, setActiveTab] = useState<'online' | 'all'>('online');
	const [allFriends, setAllFriends] = useState<FriendConnection[]>([]);
	const [loading, setLoading] = useState(false);
	const [friendStatuses, setFriendStatuses] = useState<Record<string, string>>({});
	const dropdownRef = useRef<HTMLDivElement>(null);

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

	const fetchAllFriends = async (): Promise<FriendConnection[]> => {
		if (!user?.id || !token) return [];

		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect/${user.id}`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (response.ok) {
				const connections = await response.json();
				const acceptedConnections = (connections as FriendConnection[]).filter(
					(conn) => conn.status === 'accepted'
				);

				// Deduplicate connections - only keep one record per unique friend
				const uniqueFriends = new Map<string, FriendConnection>();

				acceptedConnections.forEach((conn) => {
					// Determine who the friend is (not the current user)
					const friendId = conn.user_id === user.id ? conn.friend_id : conn.user_id;

					// Only keep one record per friend (preferring the one where current user is user_id)
					if (!uniqueFriends.has(friendId) || conn.user_id === user.id) {
						uniqueFriends.set(friendId, conn);
					}
				});

				return Array.from(uniqueFriends.values());
			}
		} catch (error) {
			console.error('Failed to fetch all friends:', error);
		}
		return [];
	};

	// Fetch all friends when the "All" tab is selected
	useEffect(() => {
		if (isOpen && activeTab === 'all' && user?.id) {
			loadConnectionsWithUsernames();
		}
	}, [isOpen, activeTab, user?.id, token]);

	// Get the status of a user from the friends object
	const getUserStatus = (userId: string): string => {
		// Return cached status if available
		if (friendStatuses[userId]) {
			return friendStatuses[userId];
		}

		// Call the Status API to get the latest status
		if (token) {
			StatusAPI.getUserStatus(userId, token)
				.then(statusResponse => {
					// Update local state instead of modifying props
					setFriendStatuses(prev => ({
						...prev,
						[userId]: statusResponse.status
					}));
				})
				.catch(error => {
					console.error(`Failed to fetch status for user ${userId}:`, error);
					setFriendStatuses(prev => ({
						...prev,
						[userId]: 'offline'
					}));
				});
		}

		return friends[userId]?.status || 'offline';
	};

	// Get the username of a user from the friends object or connection object
	const getUserName = (connection: FriendConnection, friendId: string): string => {
		// First check if we have the username from the enriched connection
		if (connection.user_id === friendId && connection.userUsername) {
			return connection.userUsername;
		}
		if (connection.friend_id === friendId && connection.friendUsername) {
			return connection.friendUsername;
		}

		// Fall back to the friends object
		if (friends[friendId]?.username) {
			return friends[friendId].username;
		}

		// Return the ID if no username is found
		return friendId;
	};

	// Load connections with usernames
	async function loadConnectionsWithUsernames() {
		setLoading(true);
		try {
			// Fetch connections
			const connections = await fetchAllFriends();

			// Deduplicate and extract unique friend IDs
			const friendIds = new Set<string>();
			const uniqueConnections = new Map<string, FriendConnection>();

			connections.forEach(conn => {
				const friendId = conn.user_id === user?.id ? conn.friend_id : conn.user_id;

				// Only process each friend once
				if (!friendIds.has(friendId)) {
					friendIds.add(friendId);
					uniqueConnections.set(friendId, conn);
				}
			});

			// Get all user IDs for the API call (including current user for completeness)
			const allUserIds = new Set<string>();
			uniqueConnections.forEach(conn => {
				allUserIds.add(conn.user_id);
				allUserIds.add(conn.friend_id);
			});

			// Fetch users
			const users = await userApi.getUsersByIds(Array.from(allUserIds));
			const userMap: Map<string, { id: string; username: string }> = new Map(
				(users as { id: string; username: string }[]).map(user => [user.id, user])
			);

			// Create enriched connections array
			const enrichedConnections = Array.from(uniqueConnections.values()).map(conn => {
				const enriched: FriendConnection = {
					...conn,
					userUsername: userMap.get(conn.user_id)?.username,
					friendUsername: userMap.get(conn.friend_id)?.username
				};
				return enriched;
			});

			setAllFriends(enrichedConnections);
		} catch (error) {
			console.error('Error loading friends with usernames:', error);
		} finally {
			setLoading(false);
		}
	}

	return (
		<div className='relative' ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className='flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none'
				aria-expanded={isOpen}
			>
				<span className='mr-1'>
					{friendCount} {friendCount === 1 ? 'friend' : 'friends'} online
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
							className={`px-4 py-2 text-sm font-medium flex-1 ${activeTab === 'online'
								? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
								: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
								}`}
							onClick={() => setActiveTab('online')}
						>
							Online ({friendCount})
						</button>
						<button
							className={`px-4 py-2 text-sm font-medium flex-1 ${activeTab === 'all'
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
							{Object.keys(friends).length > 0 ? (
								Object.values(friends).map((friend) => (
									<div
										key={friend.user_id}
										className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center'
									>
										<div
											className={`h-2 w-2 rounded-full mr-2 ${friend.status === 'online'
												? 'bg-green-500'
												: friend.status === 'away'
													? 'bg-yellow-500'
													: friend.status === 'busy'
														? 'bg-red-500'
													: 'bg-gray-500'
												}`}
										/>
										<span className='truncate'>{friend.username || friend.user_id}</span>
										<span className='ml-auto text-xs text-gray-500 dark:text-gray-400'>
											{friend.status}
										</span>
									</div>
								))
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
							{loading ? (
								<div className='py-4 px-4 text-center'>
									<div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
								</div>
							) : allFriends.length > 0 ? (
								allFriends.map((connection) => {
									const friendId = connection.user_id === user?.id ? connection.friend_id : connection.user_id;
									const status = getUserStatus(friendId) || friendStatuses[friendId];

									// Get the appropriate username
									const displayName = getUserName(connection, friendId);

									return (
										<div
											key={connection.id}
											className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center'
										>
											<div
												className={`h-2 w-2 rounded-full mr-2 ${status === 'online'
													? 'bg-green-500'
													: status === 'away'
														? 'bg-yellow-500'
														: status === 'busy'
															? 'bg-red-500'
															: 'bg-gray-500'
													}`}
											/>
											<span className='truncate'>{displayName}</span>
											<span className='ml-auto text-xs text-gray-500 dark:text-gray-400'>
												{status}
											</span>
										</div>
									);
								})
							) : (
								<div className='px-4 py-2 text-sm text-gray-500 dark:text-gray-400 italic'>
									No friends found
								</div>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default FriendsList;