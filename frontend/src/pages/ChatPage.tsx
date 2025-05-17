import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";
import type React from "react";
import { useEffect, useState } from "react";
import type { UserStatusIntf } from "../App";
import ChatList from "../components/ChatList";
import RoomList from "../components/RoomList";
import UserStatus from "../components/UserStatus";
import ConnectedUsers from "../components/ConnectedUsers";
import { useAuth, useTheme } from "../contexts";
import { useSocketContext } from "../contexts/socket/socketContext";
import { useSocketEvent } from "../contexts/socket/useSocket";
import type { Room } from "../hooks/useFetchRooms";
import { ServerEvents } from "../types/serverEvents";
import NotificationBell from "../components/NotificationsList";
import { fetchNotifications, markNotificationAsRead } from "../services/notificationsAPI";
import type { NotificationResponseType } from "../types/notificationType";

const ChatPage: React.FC = () => {
	const { darkMode, toggleDarkMode } = useTheme();
	const { user, logout } = useAuth();
	const { isConnected } = useSocketContext();
	const [friends, setFriends] = useState<Record<string, UserStatusIntf>>({});
	const [friendCount, setFriendCount] = useState(0);
	const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
	const [notifications, setNotifications] = useState<NotificationResponseType[]>([]);


	// Listen for initial friend statuses
	useSocketEvent<{ statuses: Record<string, UserStatusIntf> }>(
		ServerEvents.FRIEND_STATUSES,
		(data) => {
			setFriends(data.statuses);
		},
	);

	// Listen for individual friend status changes
	useSocketEvent<UserStatusIntf>(ServerEvents.FRIEND_STATUS_CHANGED, (data) => {
		setFriends((prev) => ({ ...prev, [data.user_id]: data }));
	});

	// Update friend count when friends change
	useEffect(() => {
		setFriendCount(Object.keys(friends).length);
	}, [friends]);


	// Fetch notifications on page load
	useEffect(() => {
		const getNotifications = async () => {
			if (user) {
				try {
					const data = await fetchNotifications(user.id);
					setNotifications(data);
				} catch (error) {
					console.error("Failed to fetch notifications:", error);
				}
			}
		};

		getNotifications();

		// Set up polling for notifications
		const interval = setInterval(getNotifications, 30000); // Check every 30 seconds

		return () => clearInterval(interval);
	}, [user]);

	// Handle marking notifications as read
	const handleMarkAsRead = async (notificationId: string) => {
		try {
			await markNotificationAsRead(notificationId);
			setNotifications(prev =>
				prev.map(notification =>
					notification.notification_id === notificationId
						? { ...notification, read: true }
						: notification
				)
			);
		} catch (error) {
			console.error("Failed to mark notification as read:", error);
		}
	};

	// Handle view all notifications
	const handleViewAll = () => {
		// Navigate to notifications page or open a modal with all notifications
		console.log("View all notifications");
	};

	if (!user) {
		return (
			<div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
				<div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500" />
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
			{/* Header/Navigation */}
			<header className="bg-white dark:bg-gray-800 shadow-sm">
				<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div className="flex justify-between items-center h-16">
						<div className="flex items-center">
							<UserStatus />
						</div>
						<div className="flex items-center space-x-4">

							<NotificationBell
								notifications={notifications}
								onMarkAsRead={handleMarkAsRead}
								onViewAll={handleViewAll}
							/>
							{/* Dark mode toggle */}
							<button
								type="button"
								onClick={toggleDarkMode}
								className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none"
								aria-label={
									darkMode ? "Switch to light mode" : "Switch to dark mode"
								}
							>
								{darkMode ? (
									<SunIcon className="h-6 w-6" />
								) : (
									<MoonIcon className="h-6 w-6" />
								)}
							</button>

							{/* Connection status indicator */}
							<div className="flex items-center">
								<div
									className={`h-2 w-2 rounded-full mr-2 ${isConnected ? "bg-green-500" : "bg-red-500"}`}
								/>
								<span className="text-sm text-gray-700 dark:text-gray-300">
									{isConnected ? "Connected" : "Disconnected"}
								</span>
							</div>

							{/* Friend count */}
							<div className="text-sm text-gray-700 dark:text-gray-300">
								{friendCount} {friendCount === 1 ? "friend" : "friends"} online
							</div>

							{/* Logout button */}
							<button
								type="button"
								onClick={logout}
								className="ml-4 px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none"
							>
								Logout
							</button>
						</div>
					</div>
				</div>
			</header>

			{/* Main content */}
			<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
				<div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
					{/* Sidebar with status */}
					<div className="lg:col-span-1">
						<RoomList onSelectRoom={setSelectedRoom} />
						<ConnectedUsers />
					</div>
					{/* Chat panel */}
					<div className="lg:col-span-2">
						{selectedRoom ? (
							<ChatList roomId={selectedRoom._id} />
						) : (
							<div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
								Select a room to start chatting
							</div>
						)}
					</div>
				</div>
			</main>
		</div>
	);
};

export default ChatPage;
