// Define the server's message format
export interface ServerMessage {
  id: string;
  senderId: string;
  senderName: string;
  recipientId?: string;
  content: string;
  timestamp: Date | string; // Allow string for API responses
  isRead: boolean;
}

// Define the props interface for the component
export interface ChatMessageProps {
  id: string;
  content: string;
  author: {
    id: string;
    username: string;
    profilePicture?: string;
  };
  timestamp: Date;
  isCurrentUser: boolean;
}

// Helper function to convert server message to component props
export const convertServerMessageToProps = (
  message: ServerMessage, 
  currentUserId: string
): ChatMessageProps => {
  return {
    id: message.id,
    content: message.content,
    author: {
      id: message.senderId,
      username: message.senderName,
      // Add profilePicture
    },
    timestamp: message.timestamp instanceof Date ? 
      message.timestamp : 
      new Date(message.timestamp),
    isCurrentUser: message.senderId === currentUserId 
  };
};