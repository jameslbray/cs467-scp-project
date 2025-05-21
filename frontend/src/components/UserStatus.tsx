import React, { useState, useRef, useEffect } from "react";
import { useUserStatus } from "../hooks/useUserStatus";
import type { StatusType } from "../types";
import { ChevronDownIcon } from "@heroicons/react/24/outline";


const UserStatus: React.FC = () => {
	const { status, isLoading, error, updateStatus } = useUserStatus();
	const [isOpen, setIsOpen] = useState(false);
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

	const handleStatusChange = (newStatus: StatusType): void => {
		updateStatus(newStatus);
		setIsOpen(false);
	};

	const getStatusColor = (statusValue: string) => {
		switch (statusValue) {
			case 'online':
				return 'bg-green-500';
			case 'away':
				return 'bg-yellow-500';
			default:
				return 'bg-gray-500';
		}
	};

	const getStatusText = (statusValue: string) => {
		return statusValue.charAt(0).toUpperCase() + statusValue.slice(1);
	};

	return (
		<div className="relative" ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className="flex items-center text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-3 py-2 rounded-md focus:outline-none"
				aria-expanded={isOpen}
				disabled={isLoading || !!error}
			>
				<div className={`h-2 w-2 rounded-full mr-2 ${getStatusColor(status)}`} />
				<span className="mr-1">
					{isLoading
						? "Loading..."
						: error
							? "Error"
							: `Status: ${getStatusText(status)}`
					}
				</span>
				<ChevronDownIcon className={`w-4 h-4 transition-transform ${isOpen ? 'transform rotate-180' : ''}`} />
			</button>

			{isOpen && !isLoading && !error && (
				<div className="absolute left-0 mt-2 py-2 w-40 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700">
					{['online', 'away', 'offline'].map((statusOption) => (
						<button
							key={statusOption}
							className={`w-full text-left px-4 py-2 text-sm ${status === statusOption
									? 'text-primary-600 dark:text-primary-400 font-medium bg-gray-100 dark:bg-gray-700'
									: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
								} flex items-center`}
							onClick={() => handleStatusChange(statusOption as StatusType)}
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