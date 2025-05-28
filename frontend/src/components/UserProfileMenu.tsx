import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/auth/authContext';
import { useUserStatus } from '../hooks/useUserStatus';
import { StatusType } from '../types';

const statusOptions = [
	{ value: StatusType.ONLINE, label: 'Online', color: 'bg-green-500' },
	{ value: StatusType.AWAY, label: 'Away', color: 'bg-yellow-500' },
	{ value: StatusType.BUSY, label: 'Busy', color: 'bg-red-500' },
	{ value: StatusType.OFFLINE, label: 'Offline', color: 'bg-gray-500' },
];

const getStatusColor = (status: StatusType) => {
	switch (status) {
		case StatusType.ONLINE:
			return 'bg-green-500';
		case StatusType.AWAY:
			return 'bg-yellow-500';
		case StatusType.BUSY:
			return 'bg-red-500';
		case StatusType.OFFLINE:
		default:
			return 'bg-gray-500';
	}
};

const UserProfileMenu: React.FC = () => {
	const { user, logout } = useAuth();
	const { status, updateStatus, isLoading: statusLoading } = useUserStatus();
	const [open, setOpen] = useState(false);
	const [statusMenuOpen, setStatusMenuOpen] = useState(false);
	const menuRef = useRef<HTMLDivElement>(null);

	// Close dropdown when clicking outside
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
				setOpen(false);
				setStatusMenuOpen(false);
			}
		}
		document.addEventListener('mousedown', handleClickOutside);
		return () => document.removeEventListener('mousedown', handleClickOutside);
	}, []);

	if (!user) return null;

	return (
		<div className='relative' ref={menuRef}>
			<button
				className='flex items-center space-x-2 px-3 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition'
				onClick={() => setOpen((v) => !v)}
				aria-haspopup='true'
				aria-expanded={open}
			>
				<span className='relative w-8 h-8 flex items-center justify-center'>
					{user.profile_picture_url ? (
						<img
							src={user.profile_picture_url}
							alt={user.username}
							className='w-8 h-8 rounded-full object-cover border border-gray-300 dark:border-gray-600'
						/>
					) : (
						<span className='w-8 h-8 flex items-center justify-center rounded-full bg-primary-500 text-white font-bold text-lg'>
							{user.username.charAt(0).toUpperCase()}
						</span>
					)}
					{/* Status dot overlay */}
					<span
						className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800 ${getStatusColor(
							status
						)}`}
					></span>
				</span>
				<span className='font-medium text-gray-900 dark:text-gray-100 hidden sm:block'>
					{user.username}
				</span>
				<ChevronDownIcon
					className={`w-4 h-4 text-gray-500 dark:text-gray-300 transition-transform ${
						open ? 'rotate-180' : ''
					}`}
				/>
			</button>
			{/* Dropdown */}
			<div
				className={`absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded shadow-lg ring-1 ring-black ring-opacity-5 z-50 transition-all duration-200 origin-top-right ${
					open ? 'scale-100 opacity-100' : 'scale-95 opacity-0 pointer-events-none'
				}`}
				style={{ minWidth: '12rem' }}
				role='menu'
				aria-orientation='vertical'
				aria-labelledby='user-menu'
			>
				<div className='py-3 px-4 border-b border-gray-100 dark:border-gray-700'>
					<div className='font-semibold text-gray-900 dark:text-gray-100'>{user.username}</div>
					<div className='text-xs text-gray-500 dark:text-gray-400'>User Settings</div>
				</div>
				{/* Set Status menu item with expandable options inside dropdown */}
				<div className='w-full'>
					<button
						className='w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between focus:outline-none transition'
						type='button'
						onClick={() => setStatusMenuOpen((v) => !v)}
						aria-expanded={statusMenuOpen}
						aria-controls='status-options'
					>
						<span className='flex items-center'>
							<span className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(status)}`}></span>
							Set Status
						</span>
						<ChevronDownIcon
							className={`w-4 h-4 ml-2 transition-transform ${statusMenuOpen ? 'rotate-180' : ''}`}
						/>
					</button>
					<div
						id='status-options'
						className={`overflow-hidden transition-all duration-200 ease-in-out ${
							statusMenuOpen ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'
						}`}
						style={{
							transitionProperty: 'max-height, opacity',
						}}
					>
						{statusOptions.map((opt) => (
							<button
								key={opt.value}
								className={`w-full text-left px-8 py-2 text-sm flex items-center space-x-2 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition ${
									status === opt.value ? 'font-bold' : ''
								}`}
								onClick={() => {
									updateStatus(opt.value);
									setStatusMenuOpen(false);
									setOpen(false);
								}}
								disabled={statusLoading}
								type='button'
							>
								<span className={`w-2.5 h-2.5 rounded-full ${opt.color}`}></span>
								<span>{opt.label}</span>
								{status === opt.value && (
									<span className='ml-auto text-xs text-primary-500'>(Current)</span>
								)}
							</button>
						))}
					</div>
				</div>
				<div className='py-2 px-4'>
					<span className='block text-gray-700 dark:text-gray-300 text-sm'>
						Settings coming soon...
					</span>
				</div>
				<div className='py-2 px-4 border-t border-gray-100 dark:border-gray-700'>
					<button
						onClick={logout}
						className='w-full px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none transition'
					>
						Logout
					</button>
				</div>
			</div>
		</div>
	);
};

export default UserProfileMenu;
