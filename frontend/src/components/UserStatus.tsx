import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/auth/authContext';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useUserStatus } from '../hooks/useUserStatus';
import type { ErrorResponse, StatusType, StatusUpdateResponse } from '../types';
import type { UserStatusType } from '../types/userStatusType';
import { FriendConnection } from '../types/friendsTypes';

type UserStatusProps = {
	friends: FriendConnection[];
};

const UserStatus: React.FC<UserStatusProps> = ({ friends }) => {
	const { status, isLoading, error, updateStatus } = useUserStatus();
	const [isOpen, setIsOpen] = useState(false);
	const [isUpdating, setIsUpdating] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const { socket, isConnected } = useSocketContext();
	const { user } = useAuth();

	const handleStatusChange = async (newStatus: StatusType) => {
		if (!socket || !isConnected) {
			return;
		}

		setIsUpdating(true);

		try {
			// Emit the standardized event name
			socket.emit('presence:status:update', { status: newStatus });

			// Wait for success/error response with timeout
			const responsePromise = new Promise<void>((resolve, reject) => {
				const timeout = setTimeout(() => {
					cleanup();
					reject(new Error('Timeout waiting for response'));
				}, 10000);

				const successHandler = (data: StatusUpdateResponse) => {
					console.log('Status update success:', data);
					updateStatus(newStatus);
					cleanup();
					resolve();
				};

				const errorHandler = (data: ErrorResponse) => {
					cleanup();
					reject(new Error(data.message || 'Status update failed'));
				};

				const cleanup = () => {
					clearTimeout(timeout);
					socket.off('presence:status:update:success', successHandler);
					socket.off('presence:status:update:error', errorHandler);
				};

				socket.on('presence:status:update:success', successHandler);
				socket.on('presence:status:update:error', errorHandler);
			});

			await responsePromise;
			setIsOpen(false);
		} catch (error) {
			console.error('Error updating status:', error);
		} finally {
			setIsUpdating(false);
		}
	};

	// Set up socket event listeners
	useEffect(() => {
		if (!socket || !isConnected) {
			return;
		}

		// Listen for friend status changes
		const handleFriendStatusChanged = (data: UserStatusType) => {

			// Update the local state or perform any necessary actions
			console.log('Friend status changed:', data);
			// You can update a state here if needed, e.g.:
			// setFriends((prev) => ({ ...prev, [data.user_id]: data }));
		};

		const handleFriendStatusesSuccess = (data: UserStatusType[]) => {
			console.log('Friend statuses received:', data);
			// You can update a state here if needed, e.g.:
			// setFriends(data);
			// Or perform any other actions with the received data
		};

		const handleFriendStatusesError = (data: { message: string }) => {
			console.error('Error fetching friend statuses:', data.message);
			// Handle the error appropriately, e.g. show a notification or log it
		};

		// Register event listeners
		socket.on('presence:friend:status:changed', handleFriendStatusChanged);
		socket.on('presence:friend:statuses:success', handleFriendStatusesSuccess);
		socket.on('presence:friend:statuses:error', handleFriendStatusesError);

		// Debug: Log all events
		const originalEmit = socket.emit;
		socket.emit = function (event, ...args) {
			return originalEmit.apply(this, [event, ...args]);
		};

		// // Request initial friend statuses when component mounts
		// if (user?.id && socket) {
		// 	setTimeout(() => {
		// 		socket.emit('presence:friend:statuses', {
		// 			user_id: user.id,
		// 			friend_ids: friends.map((friend) => friend.user_id),
		// 		});
		// 	}, 1000); // Delay to ensure connection is stable
		// }

		// Cleanup event listeners
		return () => {
			socket.off('presence:friend:status:changed', handleFriendStatusChanged);
			socket.off('presence:friend:statuses:success', handleFriendStatusesSuccess);
			socket.off('presence:friend:statuses:error', handleFriendStatusesError);
		};
	}, [socket, isConnected, user?.id, friends]);


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

	const getStatusColor = (statusValue: string) => {
		switch (statusValue) {
			case 'online':
				return 'bg-green-500';
			case 'away':
				return 'bg-yellow-500';
			case 'busy':
				return 'bg-red-500';
			case 'offline':
			default:
				return 'bg-gray-500';
		}
	};

	const getStatusText = (statusValue: string) => {
		return statusValue.charAt(0).toUpperCase() + statusValue.slice(1);
	};

	return (
		<div className='relative' ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className='flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none'
				aria-expanded={isOpen}
				disabled={isLoading || isUpdating || !!error}
			>
				<div className={`h-2 w-2 rounded-full mr-2 ${getStatusColor(status)}`} />
				<span className='mr-1'>
					{isLoading
						? 'Loading...'
						: isUpdating
						? 'Updating...'
						: error
						? 'Error'
						: `Status: ${getStatusText(status)}`}
				</span>
				<ChevronDownIcon
					className={`w-4 h-4 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
				/>
			</button>

			{isOpen && !isLoading && !isUpdating && !error && (
				<div className='absolute left-0 mt-2 py-2 w-64 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700'>
					{/* Status Options */}
					<div className='px-4 py-2 border-b border-gray-200 dark:border-gray-700'>
						<h3 className='text-sm font-medium text-gray-700 dark:text-gray-300'>Status Options</h3>
					</div>
					{['online', 'away', 'busy', 'offline'].map((statusOption) => (
						<button
							key={statusOption}
							className={`w-full text-left px-4 py-2 text-sm ${
								status === statusOption
									? 'text-primary-600 dark:text-primary-400 font-medium bg-gray-100 dark:bg-gray-700'
									: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
							} flex items-center`}
							onClick={() => handleStatusChange(statusOption as StatusType)}
							disabled={isUpdating}
						>
							<div className={`h-2 w-2 rounded-full mr-2 ${getStatusColor(statusOption)}`} />
							{getStatusText(statusOption)}
						</button>
					))}
				</div>
			)}
		</div>
	);
};

export default UserStatus;
