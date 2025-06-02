export interface NotificationResponseType {
  notification_id?: string;
  recipient_id: string;
  sender_id: string;
  sender_username?: string;
  reference_id: string;
  room_id?: string;
  room_name?: string;
  content_preview: string;
  timestamp: string;
  status: "delivered" | "undelivered" | "error";
  error?: string | null;
  read: boolean;
  notification_type: "message" | "friend_request" | "status_update" | string;
}