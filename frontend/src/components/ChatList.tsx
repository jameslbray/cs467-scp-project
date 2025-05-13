import type React from "react";
import { useEffect, useRef, useState } from "react";
import { useSocketContext } from "../contexts/socket/socketContext";
import { useFetchMessages } from "../hooks/useFetchMessages";
import type { ChatMessageType } from "../types/chatMessageType";
import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";

interface ChatListProps {
	roomId: string;
}

const ChatList: React.FC<ChatListProps> = ({ roomId }) => {
	const { socket } = useSocketContext();
	// TODO: Replace with userId from context/auth
	const currentUserId = "765e68a1-92cb-417d-aa17-9da78bb3bbdb";
	const {
		messages: initialMessages,
		loading,
		error,
	} = useFetchMessages(roomId, 50);
	const [messages, setMessages] = useState<ChatMessageType[]>([]);
	const messagesEndRef = useRef<HTMLDivElement>(null);

	// Initialize messages from backend fetch
	useEffect(() => {
		const mapped = initialMessages.map(
			(msg: ChatMessageType): ChatMessageType => ({
				id: msg.id,
				sender_id: msg.sender_id,
				room_id: msg.room_id,
				content: msg.content,
				created_at: msg.created_at,
				updated_at: msg.updated_at,
				is_edited: msg.is_edited,
				has_emoji: false,
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
		const handleIncomingMessage = (data: ChatMessageType) => {
			console.log("Received message:chat", data);
			setMessages((prev) => {
				if (prev.some((msg) => msg.id === data.id)) return prev;
				return [...prev, data];
			});
		};
		socket.on("chat:message", handleIncomingMessage);
		return () => {
			if (!socket) return;
			socket.off("chat:message", handleIncomingMessage);
		};
	}, [socket, roomId]);

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
								key={message.id}
								message={message}
								author={{ id: message.sender_id, username: message.sender_id }}
								isCurrentUser={message.sender_id === currentUserId}
							/>
						))}
						<div ref={messagesEndRef} />
					</div>
				)}
			</div>

			{/* Message Input */}
			<div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
				<ChatInput roomId={roomId} senderId={currentUserId} />
			</div>
		</div>
	);
};

export default ChatList;
