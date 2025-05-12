import type React from "react";
import { useEffect, useRef, useState } from "react";
import { useSocketContext } from "../contexts/socket/socketContext";
import { type Message, useFetchMessages } from "../hooks/useFetchMessages";
import ChatInput, { type ChatMessageData } from "./ChatInput";
import ChatMessage from "./ChatMessage";

interface ChatListProps {
	roomId: string;
}

const ChatList: React.FC<ChatListProps> = ({ roomId }) => {
	const { socket } = useSocketContext();
	// TODO: Replace with userId from context/auth and roomId from context/chat
	const currentUserId = "1";
	const {
		messages: initialMessages,
		loading,
		error,
	} = useFetchMessages(roomId, 50);
	const [messages, setMessages] = useState<ChatMessageData[]>([]);
	const messagesEndRef = useRef<HTMLDivElement>(null);

	// Initialize messages from backend fetch
	useEffect(() => {
		const mapped = initialMessages.map(
			(msg: Message): ChatMessageData => ({
				sender_id: msg.sender_id,
				room_id: msg.room_id,
				content: msg.content,
				timestamp: msg.timestamp,
				has_emoji: false, // TODO: Populate if available
			}),
		);
		setMessages(mapped);
	}, [initialMessages]);

	// Scroll to bottom whenever messages change
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	});

	// Join/leave room and listen for incoming messages
	useEffect(() => {
		if (!socket) return;
		socket.emit("join", { room: roomId });
		const handleIncomingMessage = (data: ChatMessageData) => {
			setMessages((prev) => [...prev, data]);
		};
		socket.on("chat:message", handleIncomingMessage);
		return () => {
			if (!socket) return;
			socket.emit("leave", { room: roomId });
			socket.off("chat:message", handleIncomingMessage);
		};
	}, [socket, roomId]);

	const handleSend = (message: ChatMessageData) => {
		setMessages((prev) => [...prev, message]);
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
						<p className="text-gray-500 dark:text-gray-400">
							Loading messages...
						</p>
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
								key={message.timestamp} // TODO: Use a real unique message ID if available
								id={message.timestamp}
								content={message.content}
								author={{ id: message.sender_id, username: message.sender_id }} // TODO: Replace with real user lookup
								timestamp={new Date(message.timestamp)}
								isCurrentUser={message.sender_id === currentUserId}
							/>
						))}
						<div ref={messagesEndRef} />
					</div>
				)}
			</div>

			{/* Message Input */}
			<div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
				<ChatInput
					roomId={roomId}
					senderId={currentUserId}
					onSend={handleSend}
				/>
			</div>
		</div>
	);
};

export default ChatList;
