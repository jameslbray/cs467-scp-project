export interface ChatMessageType {
  id: string;
  sender_id: string;
  room_id: string;
  content: string;
  created_at: string; // ISO string
  updated_at: string; // ISO string
  is_edited: boolean;
  has_emoji?: boolean;
  // Optionally, if you want to include author info for display:
  author?: {
    id: string;
    username: string;
    profilePicture?: string;
  };
}