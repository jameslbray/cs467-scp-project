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
export const markNotificationAsRead = async (notificationId: string): Promise<boolean> => {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) throw new Error("Authentication required");

    const response = await fetch(`${API_URL}/notify/read/${notificationId}`, {
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