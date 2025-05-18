export interface NotificationResponseType {
    notification_id?: string;
    recipient_id: string;
    sender_id: string;
    reference_id: string;
    content_preview: string;
    timestamp: string;
    status: "delivered" | "undelivered" | "error";
    error?: string | null;
    read: boolean;
    notification_type: "message" | "friend_request" | "status_update";
  }