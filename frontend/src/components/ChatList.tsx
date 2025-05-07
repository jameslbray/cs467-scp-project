import React, { useState, useRef, useEffect } from "react";
import { PaperAirplaneIcon } from "@heroicons/react/24/solid";
import {
  convertServerMessageToProps,
} from "../types/chatMessage";
import ChatMessage from "./ChatMessage";
import { User, UserStatusIntf } from "../App";
import { getConversationRoomName } from "../utils/roomUtils";

// Interface for messages from the server
export interface Message {
  id: string;
  senderId: string;
  senderName: string;
  recipientId?: string;
  content: string;
  timestamp: Date;
  isRead: boolean;
  roomName?: string;
}

// Interface for friend with status and username
interface FriendWithStatus extends UserStatusIntf {
  username: string;
}

// Props interface for the ChatList component
interface ChatListProps {
  messages: Message[];
  sendMessage: (recipientId: string, content: string) => void;
  friends: Record<string, FriendWithStatus>;
  currentUser: User;
  isConnected?: boolean;
}

const ChatList: React.FC<ChatListProps> = ({
  messages,
  sendMessage,
  friends,
  currentUser,
  isConnected = true,
}) => {
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRecipient, setSelectedRecipient] = useState<string | null>(
    null,
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Using imported room utilities instead of local helper functions
  
  // Debug: log current user ID when component mounts or updates
  useEffect(() => {
    console.log("ChatList component - Current user ID:", currentUser.id);
    console.log("Self room name would be:", getConversationRoomName(currentUser.id, currentUser.id));
  }, [currentUser.id]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!newMessage.trim() || !selectedRecipient) return;

    // Set loading state
    setIsLoading(true);

    // Send the message through socket
    sendMessage(selectedRecipient, newMessage);

    // Clear input and reset loading state
    setNewMessage("");
    setIsLoading(false);
  };

  // Select self or first friend as recipient if none is selected and friends are available
  useEffect(() => {
    if (!selectedRecipient && friends && Object.keys(friends).length > 0) {
      console.log("Available friends for chat:", Object.keys(friends).map(id => friends[id]?.username || 'Unknown'));
      
      // First check if current user is in the friends list
      if (friends[currentUser.id]) {
        console.log("Selected self as chat recipient");
        setSelectedRecipient(currentUser.id);
      } else {
        // Otherwise get the first key and verify it exists before setting it
        const firstFriendKey = Object.keys(friends)[0];
        if (firstFriendKey) {
          console.log("Selected friend as chat recipient:", friends[firstFriendKey]?.username || 'Unknown');
          setSelectedRecipient(firstFriendKey);
        }
      }
    }
  }, [friends, selectedRecipient, currentUser.id]);

  return (
    <div className="flex flex-col h-[600px] bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      {/* Chat Header with Recipient Selection */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {selectedRecipient && friends && friends[selectedRecipient]
                ? selectedRecipient === currentUser.id
                  ? "Self Messages (Note to Self)"
                  : `Chat with ${friends[selectedRecipient].username}`
                : "Select a friend to chat with"}
            </h2>
            {!isConnected && (
              <span className="text-xs text-red-500 mt-1 inline-block">
                Offline mode - Messages will be sent when connection is restored
              </span>
            )}
          </div>

          {/* Friend selector dropdown */}
          <select
            className={`px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm
                      focus:outline-none focus:ring-primary-500 focus:border-primary-500
                      dark:bg-gray-700 dark:text-white text-sm
                      ${!isConnected ? 'opacity-75' : ''}`}
            value={selectedRecipient || ""}
            onChange={(e) => setSelectedRecipient(e.target.value)}
          >
            <option value="" disabled>
              Select a friend
            </option>
            {Object.entries(friends).map(([id, friend]) => (
              <option key={id} value={id}>
                {friend.username} ({friend.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 p-4 overflow-y-auto bg-gray-50 dark:bg-gray-900">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 dark:text-gray-400">
              {selectedRecipient
                ? "No messages yet. Start a conversation!"
                : "Select a friend to start chatting"}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Filter messages for the selected conversation, including self-messages */}
            {/* Filter messages for the selected conversation */}
            {messages
              .filter(
                (msg) => {
                  // If the message has a roomName field, use that for filtering
                  if (msg.roomName) {
                    // Get the expected room name based on the selected recipient
                    const expectedRoomName = getConversationRoomName(currentUser.id, selectedRecipient || "");
                    console.log(`Comparing message room: ${msg.roomName} with expected room: ${expectedRoomName}`);
                    
                    // Compare the actual room name with the expected one
                    return msg.roomName === expectedRoomName;
                  }
                  
                  // Fallback to the old filtering method for backwards compatibility
                  // For self-messaging, show messages where both sender and recipient are the current user
                  if (selectedRecipient === currentUser.id) {
                    return msg.senderId === currentUser.id && msg.recipientId === currentUser.id;
                  }
                  
                  // For normal conversations
                  return (msg.senderId === selectedRecipient &&
                          msg.recipientId === currentUser.id) ||
                         (msg.recipientId === selectedRecipient &&
                          msg.senderId === currentUser.id);
                }
              )
              .map((message) => {
                // Convert the message format
                const props = convertServerMessageToProps(
                  message,
                  currentUser.id,
                );
                // Pass all props individually
                return (
                  <ChatMessage
                    key={message.id}
                    id={props.id}
                    content={props.content}
                    author={props.author}
                    timestamp={props.timestamp}
                    isCurrentUser={props.isCurrentUser === true}
                  />
                );
              })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Message Input */}
      <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        {!isConnected && (
          <div className="mb-2 p-2 bg-yellow-100 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-100 text-sm rounded">
            <span className="font-semibold">⚠️ Connection lost:</span> Messages will be queued until connection is restored
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <div className="flex-1">
            <textarea
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white"
              placeholder={
                selectedRecipient
                  ? selectedRecipient === currentUser.id
                    ? "Type a note to yourself... (Markdown supported)"
                    : "Type your message here... (Markdown supported)"
                  : "Select a friend to chat with"
              }
              rows={3}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              disabled={isLoading || !selectedRecipient || !isConnected}
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Supports Markdown: **bold**, *italic*, `code`, ```code blocks```,
              [links](url), and lists
            </p>
          </div>
          <button
            type="submit"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed h-10"
            disabled={isLoading || !newMessage.trim() || !selectedRecipient}
            title={!isConnected ? "Messages will be sent when connection is restored" : ""}
          >
            {isLoading ? (
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <PaperAirplaneIcon className="h-5 w-5" />
            )}
            <span className="sr-only">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatList;
