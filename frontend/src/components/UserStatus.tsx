import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/auth/authContext';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useUserStatus } from '../hooks/useUserStatus';
import type { ErrorResponse, StatusType, StatusUpdateResponse } from '../types';
import type { UserStatusType } from '../types/userStatusType';

type UserStatusProps = {
	friends: UserStatusType[];
};

const UserStatus: React.FC<UserStatusProps> = ({ friends }) => {
	const { status, isLoading, error, updateStatus } = useUserStatus();
	const [isOpen, setIsOpen] = useState(false);
	const [isUpdating, setIsUpdating] = useState(false);
	const [debugInfo, setDebugInfo] = useState<string[]>([]);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const { socket, isConnected } = useSocketContext();
	const { user } = useAuth();

	// Debug function to add messages
	const addDebugInfo = (message: string) => {
		console.log(`[UserStatus Debug] ${message}`);
		setDebugInfo((prev) => [...prev.slice(-4), `${new Date().toLocaleTimeString()}: ${message}`]);
	};

	const handleStatusChange = async (newStatus: StatusType) => {
		if (!socket || !isConnected) {
			addDebugInfo('Socket not connected');
			return;
		}

		setIsUpdating(true);
		addDebugInfo(`Attempting to change status to: ${newStatus}`);

		try {
			// Emit the standardized event name
			addDebugInfo(`Emitting presence:status:update event`);
			socket.emit('presence:status:update', { status: newStatus });

			// Wait for success/error response with timeout
			const responsePromise = new Promise<void>((resolve, reject) => {
				const timeout = setTimeout(() => {
					addDebugInfo('Response timeout after 10 seconds');
					cleanup();
					reject(new Error('Timeout waiting for response'));
				}, 10000);

				const successHandler = (data: StatusUpdateResponse) => {
					addDebugInfo(`Success response received: ${JSON.stringify(data)}`);
					updateStatus(newStatus);
					cleanup();
					resolve();
				};

				const errorHandler = (data: ErrorResponse) => {
					addDebugInfo(`Error response received: ${JSON.stringify(data)}`);
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
			addDebugInfo('Status update completed successfully');
		} catch (error) {
			addDebugInfo(`Error updating status: ${error}`);
			console.error('Error updating status:', error);
		} finally {
			setIsUpdating(false);
		}
	};

	const handleGetFriendStatuses = () => {
		if (!socket || !isConnected) {
			addDebugInfo('Socket not connected for friend statuses');
			return;
		}

		addDebugInfo('Requesting friend statuses');
		socket.emit('presence:friend:statuses');
	};

	// Set up socket event listeners
	useEffect(() => {
		if (!socket || !isConnected) {
			addDebugInfo('Socket not available for event listeners');
			return;
		}

		addDebugInfo('Setting up socket event listeners');

		// Listen for friend status changes
		const handleFriendStatusChanged = (data: UserStatusType) => {
			addDebugInfo(`Friend status changed: ${JSON.stringify(data)}`);
		};

		const handleFriendStatusesSuccess = (data: UserStatusType[]) => {
			addDebugInfo(`Friend statuses received: ${JSON.stringify(data)}`);
		};

		const handleFriendStatusesError = (data: { message: string }) => {
			addDebugInfo(`Friend statuses error: ${JSON.stringify(data)}`);
		};

		// Register event listeners
		socket.on('presence:friend:status:changed', handleFriendStatusChanged);
		socket.on('presence:friend:statuses:success', handleFriendStatusesSuccess);
		socket.on('presence:friend:statuses:error', handleFriendStatusesError);

		// Debug: Log all events
		const originalEmit = socket.emit;
		socket.emit = function (event, ...args) {
			addDebugInfo(`Emitting event: ${event} with args: ${JSON.stringify(args)}`);
			return originalEmit.apply(this, [event, ...args]);
		};

		// Request initial friend statuses when component mounts
		if (user?.id && socket) {
			addDebugInfo(`Requesting initial friend statuses for user ${user.id}`);
			setTimeout(() => {
				socket.emit('presence:friend:statuses', {
					user_id: user.id,
					friend_ids: friends.map((friend) => friend.user_id),
				});
			}, 1000); // Delay to ensure connection is stable
		}

		// Cleanup event listeners
		return () => {
			addDebugInfo('Cleaning up socket event listeners');
			socket.off('presence:friend:status:changed', handleFriendStatusChanged);
			socket.off('presence:friend:statuses:success', handleFriendStatusesSuccess);
			socket.off('presence:friend:statuses:error', handleFriendStatusesError);
		};
	}, [socket, isConnected, user?.id, friends]);

	// Log socket connection status changes
	useEffect(() => {
		addDebugInfo(`Socket connection status: ${isConnected ? 'Connected' : 'Disconnected'}`);
	}, [isConnected]);

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

					{/* Debug Section */}
					<div className='px-4 py-2 border-t border-gray-200 dark:border-gray-700'>
						<h3 className='text-xs font-medium text-gray-500 dark:text-gray-400 mb-2'>
							Debug Info
						</h3>
						<button
							onClick={handleGetFriendStatuses}
							className='w-full text-left px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded mb-2'
						>
							Test Friend Statuses Request
						</button>
						<div className='text-xs text-gray-500 dark:text-gray-400 max-h-20 overflow-y-auto'>
							{debugInfo.map((info, index) => (
								<div key={index} className='truncate'>
									{info}
								</div>
							))}
						</div>
						<div className='text-xs text-gray-500 dark:text-gray-400 mt-1'>
							Socket: {isConnected ? '✅ Connected' : '❌ Disconnected'}
						</div>
					</div>
				</div>
			)}
		</div>
	);
};

export default UserStatus;
