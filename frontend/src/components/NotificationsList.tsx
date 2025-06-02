import { BellIcon, BellSlashIcon } from "@heroicons/react/24/outline";
import { BellIcon as BellIconSolid } from "@heroicons/react/24/solid";
import React, { useRef, useState, useEffect } from "react";
import { useClickAway } from "react-use";
import type { NotificationResponseType } from "../types/notificationType";
import { formatRelativeTime } from "../utils/dateUtils";
import { markNotificationAsRead } from "../services/notificationsAPI";
import { fetchNotifications, deleteNotification, markAllNotificationsAsRead } from "../services/notificationsAPI";
import { useAuth } from "../contexts/auth/authContext";
import { useSocketContext } from '../contexts/socket/socketContext';
import { userApi } from "../services/api";
import type { User } from "../types/userType";

interface NotificationBellProps {
  className?: string;
}

const NotificationBell: React.FC<NotificationBellProps> = ({
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<NotificationResponseType[]>([]);
  const [displayCount, setDisplayCount] = useState<number>(5);
  const { user } = useAuth();
  const { socket } = useSocketContext();
  const [userMap, setUserMap] = useState<Record<string, User>>({});

  // Close dropdown when clicking outside
  useClickAway(ref, () => {
    setIsOpen(false);
    setDisplayCount(5);
  });

  // Count unread notifications
  const unreadCount = notifications.filter(n => !n.read).length;

  // Socket event listener for new notifications
  useEffect(() => {
    if (!socket) return;

    const handleNewNotification = (notification: NotificationResponseType) => {
      console.log('Received new notification:', notification);
      // Add the new notification to the list and sort
      setNotifications(prev => {
        // Check if we already have this notification to avoid duplicates
        if (prev.some(n => n.notification_id === notification.notification_id)) {
          return prev;
        }

        const updated = [notification, ...prev];
        return updated.sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
      });
    };

    socket.on('notification:new', handleNewNotification);

    return () => {
      socket.off('notification:new', handleNewNotification);
    };
  }, [socket]);

  useEffect(() => {
    if (notifications.length > 0) {
      fetchUsernames(notifications);
    }
  }, [notifications]);

  const fetchUsernames = async (notifications: NotificationResponseType[]) => {
    if (notifications.length === 0) return;

    // Collect all user IDs that need username lookup
    const userIds = new Set<string>();
    notifications.forEach((notification) => {
      if (notification.sender_id) userIds.add(notification.sender_id);
      if (notification.recipient_id) userIds.add(notification.recipient_id);
    });

    // Remove current user's ID
    if (user?.id) userIds.delete(user.id);

    // Don't make API call if no IDs to fetch
    if (userIds.size === 0) return;

    // Fetch user details
    try {
      const users = await userApi.getUsersByIds(Array.from(userIds));

      // Create a map of user IDs to user objects for easy lookup
      const newUserMap: Record<string, User> = {};
      users.forEach((user: User) => {
        newUserMap[user.id] = user;
      });

      // Update the user map state
      setUserMap(prev => ({ ...prev, ...newUserMap }));
    } catch (error) {
      console.error('Failed to fetch user details:', error);
    }
  };

  // Update the notification rendering to use usernames
  const getUserDisplayName = (userId: string) => {
    // If we have the user in our map, return their username or display name
    if (userMap[userId]) {
      return userMap[userId].username ||
        userMap[userId].display_name ||
        userId.substring(0, 8) + '...';
    }
    // Fallback to truncated ID
    return userId.substring(0, 8) + '...';
  };


  // Handle marking notifications as read
  const handleMarkAsRead = async (notificationId: string, recipientId: string) => {
    try {
      await markNotificationAsRead(notificationId, recipientId);
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
    // If we're already showing all, don't do anything
    if (displayCount >= notifications.length) return;

    // If we're showing 5 or more, show all
    else {
      setDisplayCount(notifications.length);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      // Mark all notifications as read
      if (user) {
        await markAllNotificationsAsRead(user.id);

        // Update state to reflect that all notifications are read
        setNotifications(prev =>
          prev.map(notification => ({ ...notification, read: true }))
        );
      }
    }
    catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }

  // Fetch notifications on page load
  useEffect(() => {
    const getNotifications = async () => {
      if (user) {
        try {
          // First fetch the current notifications
          const currentData = await fetchNotifications(user.id);

          // Check if there are any read notifications to delete
          const readNotifications = currentData.filter(notification => notification.read);
          if (readNotifications.length > 0) {
            await deleteNotification(user.id);
          }

          // Re-fetch to get the clean list after deletion
          const updatedData = await fetchNotifications(user.id);

          // Sort notifications by timestamp (newest first)
          const sortedData = updatedData.sort((a, b) => {
            return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
          });

          setNotifications(sortedData);
        } catch (error) {
          console.error("Failed to fetch notifications:", error);
        }
      }
    };

    getNotifications();

    // Set up polling for notifications
    const interval = setInterval(getNotifications, 300000); // Check every 5 minutes as backup

    return () => clearInterval(interval);
  }, [user]);

  // Rest of the component remains the same
  return (
    <div className={`relative ${className}`} ref={ref}>
      {/* Bell button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none"
        aria-label="Notifications"
      >
        {/* Rest of the button content remains the same */}
        {notifications.length === 0 ? (
          <BellSlashIcon className="h-6 w-6" />
        ) : (
          <>
            {unreadCount > 0 ? (
              <BellIconSolid className="h-6 w-6" />
            ) : (
              <BellIcon className="h-6 w-6" />
            )}

            {/* Notification indicator */}
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </>
        )}
      </button>

      {/* Dropdown content */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-md shadow-lg overflow-hidden z-50 border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">Notifications</h3>
            {notifications.length > 0 && (<div>
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-slate-800 dark:text-slate-400 hover:underline px-5"
              >
                Mark all as read
              </button>

              <button
                onClick={handleViewAll}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                View all
              </button>
            </div>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
                No notifications
              </div>
            ) : (
              <ul>
                {/* Notifications exist */}
                {notifications.slice(0, displayCount).map((notification) => (
                  <li key={notification.notification_id || Math.random().toString()}
                    className={`px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 ${!notification.read ? "bg-blue-50 dark:bg-blue-900/20" : ""}`}
                    onClick={() => {
                      // Mark as read when clicking anywhere in the notification
                      if (notification.notification_id && user) {
                        handleMarkAsRead(notification.notification_id, user.id);
                      }
                    }}
                  >
                    <div className="cursor-pointer">
                      <div className="flex justify-between">
                        {/* Title/preview content */}
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {(notification.notification_type || notification.notification_type) === 'chat_message' && notification.room_name ?
                              `New message in ${notification.room_name}` :
                              notification.content_preview}
                          </p>
                          {/* Timestamp */}
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {formatRelativeTime(notification.timestamp)}
                          </span>
                        </div>
                        {/* Sender name */}
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                          From {notification.sender_username || getUserDisplayName(notification.sender_id)}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}

                {/* View more notifications */}
                {notifications.length > displayCount && (
                  <li className="p-2 text-center">
                    <button
                      onClick={handleViewAll}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      View {notifications.length - displayCount} more
                    </button>
                  </li>
                )}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;