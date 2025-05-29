import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts';
import { userApi } from '../services/api';

interface User {
	id: string;
	username: string;
	profilePicture?: string;
}

interface Connection {
	id?: string;
	user_id: string;
	friend_id: string;
	status: 'pending' | 'accepted' | 'rejected' | 'blocked';
	created_at?: string;
	updated_at?: string;
}

interface SearchUsersProps {
	onConnectionChange?: () => void;
}

const CONNECT_API_URL = 'http://localhost:8005';
const USERS_API_URL = 'http://localhost:8001';

const SearchUsers: React.FC<SearchUsersProps> = ({ onConnectionChange }) => {
	const { user, token } = useAuth();
	const [searchTerm, setSearchTerm] = useState('');
	const [isOpen, setIsOpen] = useState(false);
	const [isLoading, setIsLoading] = useState(false);
	const [searchResults, setSearchResults] = useState<User[]>([]);
	const [pendingRequests, setPendingRequests] = useState<Connection[]>([]);
	const [userConnections, setUserConnections] = useState<Connection[]>([]);
	const [activeTab, setActiveTab] = useState<'search' | 'requests'>('search');
	const dropdownRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);

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

	// Get pending friend requests and user connections when component mounts
	useEffect(() => {
		if (user) {
			fetchUserConnections();
			fetchPendingRequests();
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [user]);

	useEffect(() => {
		const fetchUsernames = async () => {
			if (pendingRequests.length === 0) return;
			// Collect all user IDs that need username lookup
			const userIds = new Set<string>();
			pendingRequests.forEach((req) => {
				userIds.add(req.user_id);
				userIds.add(req.friend_id);
			});
			// Remove current user's ID
			if (user?.id) userIds.delete(user.id);
			// Fetch user details
			try {
				const users = await userApi.getUsersByIds(Array.from(userIds));
				setSearchResults((prev) => {
					// Merge with existing results without duplicates
					const existingIds = new Set(prev.map((u) => u.id));
					const newUsers: User[] = users.filter((u: User) => !existingIds.has(u.id));
					return [...prev, ...newUsers];
				});
			} catch (error) {
				console.error('Failed to fetch user details:', error);
			}
		};
		fetchUsernames();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [pendingRequests]);

	// Focus input when dropdown is opened
	useEffect(() => {
		if (isOpen && inputRef.current) {
			inputRef.current.focus();
		}
	}, [isOpen]);

	// Fetch user connections
	const fetchUserConnections = async () => {
		if (!user?.id || !token) return;
		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect/${user.id}`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});
			if (response.ok) {
				const connections = await response.json();
				// Store ALL connections where this user is involved (not just accepted)
				setUserConnections(
					connections.filter(
						(conn: Connection) => conn.user_id === user.id || conn.friend_id === user.id
					)
				);
			}
		} catch (error) {
			console.error('Failed to fetch user connections:', error);
		}
	};

	// Fetch pending requests
	const fetchPendingRequests = async () => {
		if (!user?.id || !token) return;
		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect/${user.id}`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});
			if (response.ok) {
				const connections = await response.json();
				// Only incoming requests: friend_id === user.id && status === 'pending'
				const incoming = connections.filter(
					(conn: Connection) => conn.friend_id === user.id && conn.status === 'pending'
				);
				setPendingRequests(incoming);
			}
		} catch (error) {
			console.error('Failed to fetch pending requests:', error);
		}
	};

	// Search for users
	const searchUsers = async () => {
		if (!searchTerm.trim() || !token) return;
		setIsLoading(true);
		try {
			// Make API call to search users by username
			const response = await fetch(
				`${USERS_API_URL}/users/search?username=${encodeURIComponent(searchTerm)}`,
				{
					headers: {
						Authorization: `Bearer ${token}`,
					},
				}
			);
			if (response.ok) {
				const users = await response.json();
				// Filter out the current user
				setSearchResults(users.filter((u: User) => u.id !== user?.id));
			}
		} catch (error) {
			console.error('Failed to search users:', error);
		} finally {
			setIsLoading(false);
		}
	};

	// Handle search input changes
	const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setSearchTerm(e.target.value);
		if (e.target.value.trim().length >= 2) {
			searchUsers();
		} else {
			setSearchResults([]);
		}
	};

	// Send a friend request
	const sendFriendRequest = async (friendId: string) => {
		if (!user?.id || !token) return;
		if (getConnectionStatus(friendId) === 'pending') {
			return;
		}
		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					user_id: user.id,
					friend_id: friendId,
					status: 'pending',
				}),
			});
			if (response.ok) {
				fetchUserConnections();
				fetchPendingRequests();
				if (onConnectionChange) onConnectionChange();
			}
		} catch (error) {
			console.error('Failed to send friend request:', error);
		}
	};

	// Accept a friend request
	const acceptRequest = async (connection: Connection) => {
		if (!user?.id || !token) return;
		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
				method: 'PUT',
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					user_id: connection.user_id, // sender
					friend_id: user.id, // recipient
					status: 'accepted',
				}),
			});
			if (response.ok) {
				fetchPendingRequests();
				fetchUserConnections();
				if (onConnectionChange) onConnectionChange();
			}
		} catch (error) {
			console.error('Failed to accept friend request:', error);
		}
	};

	// Reject a friend request
	const rejectRequest = async (connection: Connection) => {
		if (!user?.id || !token) return;
		try {
			const response = await fetch(`${CONNECT_API_URL}/api/connect`, {
				method: 'PUT',
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					user_id: connection.user_id, // sender
					friend_id: user.id, // recipient
					status: 'rejected',
				}),
			});
			if (response.ok) {
				fetchPendingRequests();
				if (onConnectionChange) onConnectionChange();
			}
		} catch (error) {
			console.error('Failed to reject friend request:', error);
		}
	};

	const getConnectionStatus = (userId: string): string | null => {
		// Find all connections between the current user and userId
		const connections = [...userConnections, ...pendingRequests].filter(
			(conn) =>
				(conn.user_id === user?.id && conn.friend_id === userId) ||
				(conn.user_id === userId && conn.friend_id === user?.id)
		);
		if (connections.length === 0) return null;
		// Sort by created_at descending and pick the latest
		const latest = connections.slice().sort((a, b) => {
			const aTime = new Date(a.created_at ?? 0).getTime();
			const bTime = new Date(b.created_at ?? 0).getTime();
			return bTime - aTime;
		})[0];
		if (!latest) return null;
		return latest.status;
	};

	// Render connection button based on status
	const renderConnectionButton = (userId: string) => {
		const connections = [...userConnections, ...pendingRequests].filter(
			(conn) =>
				(conn.user_id === user?.id && conn.friend_id === userId) ||
				(conn.user_id === userId && conn.friend_id === user?.id)
		);
		if (connections.length === 0) {
			return (
				<button
					onClick={() => sendFriendRequest(userId)}
					className='text-xs bg-primary-500 hover:bg-primary-600 text-white px-2 py-1 rounded'
				>
					Connect
				</button>
			);
		}
		const latest = connections.slice().sort((a, b) => {
			const aTime = new Date(a.created_at ?? 0).getTime();
			const bTime = new Date(b.created_at ?? 0).getTime();
			return bTime - aTime;
		})[0];
		if (!latest) {
			return (
				<button
					onClick={() => sendFriendRequest(userId)}
					className='text-xs bg-primary-500 hover:bg-primary-600 text-white px-2 py-1 rounded'
				>
					Connect
				</button>
			);
		}
		if (latest.status === 'accepted') {
			return <span className='text-green-500 text-xs'>Connected</span>;
		}
		if (latest.status === 'pending') {
			if (latest.user_id === user?.id && latest.friend_id === userId) {
				return <span className='text-yellow-500 text-xs'>Request Sent</span>;
			} else if (latest.user_id === userId && latest.friend_id === user?.id) {
				return <span className='text-yellow-500 text-xs'>Request Received</span>;
			}
		}
		if (latest.status === 'rejected') {
			return <span className='text-red-500 text-xs'>Rejected</span>;
		}
		if (latest.status === 'blocked') {
			return null;
		}
		return (
			<button
				onClick={() => sendFriendRequest(userId)}
				className='text-xs bg-primary-500 hover:bg-primary-600 text-white px-2 py-1 rounded'
			>
				Connect
			</button>
		);
	};

	return (
		<div className='relative' ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className='flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none'
				aria-expanded={isOpen}
			>
				<MagnifyingGlassIcon className='h-5 w-5 mr-1' />
				<span>Find Friends</span>
				{pendingRequests.length > 0 && (
					<span className='ml-2 bg-red-500 text-white rounded-full h-5 w-5 flex items-center justify-center text-xs'>
						{pendingRequests.length}
					</span>
				)}
			</button>

			{isOpen && (
				<div className='absolute right-0 mt-2 py-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg z-20 border border-gray-200 dark:border-gray-700'>
					{/* Tabs */}
					<div className='flex border-b border-gray-200 dark:border-gray-700'>
						<button
							className={`px-4 py-2 text-sm font-medium flex-1 ${
								activeTab === 'search'
									? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
							}`}
							onClick={() => setActiveTab('search')}
						>
							Search
						</button>
						<button
							className={`px-4 py-2 text-sm font-medium flex-1 ${
								activeTab === 'requests'
									? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-500'
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
							}`}
							onClick={() => setActiveTab('requests')}
						>
							Requests {pendingRequests.length > 0 && `(${pendingRequests.length})`}
						</button>
					</div>

					{/* Search Tab */}
					{activeTab === 'search' && (
						<>
							<div className='px-4 py-2'>
								<div className='relative'>
									<input
										ref={inputRef}
										type='text'
										placeholder='Search users...'
										value={searchTerm}
										onChange={handleSearchChange}
										className='w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500'
									/>
									{searchTerm && (
										<button
											onClick={() => {
												setSearchTerm('');
												setSearchResults([]);
											}}
											className='absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
										>
											<XMarkIcon className='h-4 w-4' />
										</button>
									)}
								</div>
							</div>

							<div className='max-h-60 overflow-y-auto'>
								{isLoading ? (
									<div className='py-4 px-4 text-center'>
										<div className='animate-spin h-5 w-5 mx-auto border-t-2 border-b-2 border-primary-500 rounded-full'></div>
									</div>
								) : searchResults.length > 0 ? (
									searchResults.map((result) => (
										<div
											key={result.id}
											className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between'
										>
											<div className='flex items-center'>
												<div className='w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 overflow-hidden mr-2'>
													{result.profilePicture ? (
														<img
															src={result.profilePicture}
															alt={result.username}
															className='w-full h-full object-cover'
														/>
													) : (
														<div className='w-full h-full flex items-center justify-center text-gray-600 dark:text-gray-400'>
															{result.username.charAt(0).toUpperCase()}
														</div>
													)}
												</div>
												<span className='truncate font-medium'>{result.username}</span>
											</div>
											{renderConnectionButton(result.id)}
										</div>
									))
								) : searchTerm ? (
									<div className='px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center'>
										No users found
									</div>
								) : (
									<div className='px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center'>
										Type at least 2 characters to search
									</div>
								)}
							</div>
						</>
					)}

					{/* Requests Tab */}
					{activeTab === 'requests' && (
						<div className='max-h-60 overflow-y-auto'>
							{pendingRequests.length > 0 ? (
								pendingRequests.map((request) => {
									// Use usernames instead of IDs if available
									const senderUsername =
										searchResults.find((u) => u.id === request.user_id)?.username ||
										request.user_id;
									return (
										<div
											key={request.id || `${request.user_id}-${request.friend_id}`}
											className='px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
										>
											<div className='flex items-center justify-between mb-2'>
												<div className='flex items-center'>
													<div className='w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 overflow-hidden mr-2'>
														<div className='w-full h-full flex items-center justify-center text-gray-600 dark:text-gray-400'>
															{senderUsername.charAt(0).toUpperCase()}
														</div>
													</div>
													<span className='truncate font-medium'>{senderUsername}</span>
												</div>
											</div>
											<div className='flex space-x-2 mt-1'>
												<button
													onClick={() => acceptRequest(request)}
													className='flex-1 bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded text-xs'
												>
													Accept
												</button>
												<button
													onClick={() => rejectRequest(request)}
													className='flex-1 bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs'
												>
													Reject
												</button>
											</div>
										</div>
									);
								})
							) : (
								<div className='px-4 py-3 text-sm text-gray-500 dark:text-gray-400 italic text-center'>
									No pending requests
								</div>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default SearchUsers;
