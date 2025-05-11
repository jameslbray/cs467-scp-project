import React, { useState, useRef, useEffect } from "react";
import { PaperAirplaneIcon } from "@heroicons/react/24/solid";
import ChatMessage from "./ChatMessage";
import { useFetchMessages } from "../hooks/useFetchMessages";

const ChatList: React.FC = () => {
  // Placeholder token and roomId for demonstration; replace with real values from context/auth
  const token = "YOUR_JWT_TOKEN_HERE"; // TODO: Replace with real token from auth context
  const roomId = "general";

  const { messages, loading, error } = useFetchMessages(roomId, token);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    setIsLoading(true);
    // Simulate sending a message (in real app, send via socket or API)
    setTimeout(() => {
      // For demo, just clear the input
      setNewMessage("");
      setIsLoading(false);
    }, 500);
  };

  return (
    <div className="flex flex-col h-[600px] bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
          Chat Room
        </h2>
      </div>

      {/* Messages Container */}
      <div className="flex-1 p-4 overflow-y-auto bg-gray-50 dark:bg-gray-900">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 dark:text-gray-400">Loading messages...</p>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-red-500 dark:text-red-400">Error: {error}</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 dark:text-gray-400">No messages yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <ChatMessage
                key={message._id}
                id={message._id}
                content={message.content}
                author={{ id: message.sender_id, username: message.sender_id }} // TODO: Replace with real user lookup
                timestamp={new Date(message.timestamp)}
                isCurrentUser={message.sender_id === "1"} // TODO: Replace with real current user id
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Message Input */}
      <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <div className="flex-1">
            <label
              htmlFor="message-input"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Message
            </label>
            <textarea
              id="message-input"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white"
              placeholder="Type your message here... (Markdown supported)"
              rows={3}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              disabled={isLoading}
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Supports Markdown: **bold**, *italic*, `code`, ```code blocks```,
              [links](url), and lists
            </p>
          </div>
          <button
            type="submit"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed h-10"
            disabled={isLoading || !newMessage.trim()}
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
