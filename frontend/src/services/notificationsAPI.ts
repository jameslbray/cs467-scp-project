import type { NotificationResponseType } from "../types/notificationType";


const API_URL = "http://localhost:8002/api";

/**
 * Fetch notifications for a user
 */
export const fetchNotifications = async (userId: string): Promise<NotificationResponseType[]> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    const response = await fetch(`${API_URL}/notify/${userId}`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    if (!response.ok) throw new Error("Failed to fetch notifications");

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching notifications:", error);
    return [];
  }
};

/**
 * Mark a notification as read
 */
export const markNotificationAsRead = async (notificationId: string, recipientId: string): Promise<boolean> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    // TODO: Do we need to pass a list of notification IDs or just one?
    const response = await fetch(`${API_URL}/notify/${recipientId}?notification_id=${notificationId}`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    return response.ok;
  } catch (error) {
    console.error("Error marking notification as read:", error);
    return false;
  }
};

/**
 * Mark all notifications as read
 */
export const markAllNotificationsAsRead = async (recipientId: string): Promise<boolean> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    // TODO: Finish implementing this
    const response = await fetch(`${API_URL}/notify/all/${recipientId}`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    return response.ok;
  } catch (error) {
    console.error("Error marking notification as read:", error);
    return false;
  }
};


/**
 * Create a new notification for a user
 */
export const createNotification = async (
  userId: string,
  senderId: string,
  referenceId: string,
  content_preview: string,
  notification_type: string
): Promise<NotificationResponseType[]> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    const response = await fetch(`${API_URL}/notify/${userId}`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      method: "POST",
      body: JSON.stringify({
        recipient_id: userId,
        sender_id: senderId,
        reference_id: referenceId,
        content_preview: content_preview,
        timestamp: new Date().toISOString(),
        status: "undelivered",
        read: false,
        notification_type: notification_type
      }),
    });

    if (!response.ok) throw new Error("Failed to create notification");

    const data = await response.json();
    if (data.error || data === null) {
      console.error("Error creating notification:", data.error);
      return [];
    }
    return data;
  } catch (error) {
    console.error("Error creating notification:", error);
    return [];
  }
};

/**
 * Delete all read notifications
 */
export const deleteNotification = async (recipientId: string): Promise<boolean> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    const response = await fetch(`${API_URL}/notify/${recipientId}`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    return response.ok || response.status === 404;
  } catch (error) {
    console.error("Error deleting notification:", error);
    return false;
  }
}