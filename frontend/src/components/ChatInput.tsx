import type React from "react";
import { useState } from "react";
import { getSocket } from "../socket/socket";

export interface ChatMessageData {
	sender_id: string;
	room_id: string;
	content: string;
	timestamp: string;
	has_emoji: boolean;
}

interface ChatInputProps {
	roomId: string;
	senderId: string;
	onSend?: (message: ChatMessageData) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ roomId, senderId, onSend }) => {
	const [message, setMessage] = useState("");
	const token = localStorage.getItem("auth_token");
	if (!token) {
		throw new Error("No auth token found");
	}
	const socket = getSocket(token);

	const handleSend = () => {
		if (message.trim() === "") return;

		const messageData: ChatMessageData = {
			sender_id: senderId,
			room_id: roomId,
			content: message,
			timestamp: new Date().toISOString(),
			has_emoji: false,
		};

		socket.emit("chat_message", messageData);
		if (onSend) onSend(messageData);
		setMessage("");
	};

	return (
		<div className="flex gap-2 items-center mt-4">
			<input
				type="text"
				placeholder="Type a message..."
				className="flex-grow border px-4 py-2 rounded shadow"
				value={message}
				onChange={(e) => setMessage(e.target.value)}
				onKeyDown={(e) => e.key === "Enter" && handleSend()}
			/>
			<button
				type="button"
				onClick={handleSend}
				className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
			>
				Send
			</button>
		</div>
	);
};

export default ChatInput;
