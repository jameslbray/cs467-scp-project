import { useEffect, useState } from "react";
import type { ChatMessageType } from "../types/chatMessageType";

export function useFetchMessages(roomId: string, limit = 50) {
	const [messages, setMessages] = useState<ChatMessageType[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!roomId) {
			console.error("Room ID is required");
			setLoading(true);
			setError("Room ID is required");
			return;
		}

		const token = localStorage.getItem("auth_token");
		if (!token) {
			console.error("No auth token found");
			setLoading(true);
			setError("No auth token found");
			return;
		}

		const fetchMessages = async () => {
			try {
				const response = await fetch(
					`http://localhost:8004/rooms/${roomId}/messages?limit=${limit}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
				);
				console.log("Response:", response);

				if (!response.ok) {
					console.error("Failed to fetch messages:", response.statusText);
					throw new Error(`Failed to fetch messages: ${response.statusText}`);
				}

				const data = await response.json();
				console.log("Data:", data);
				setMessages(data);
			} catch (err) {
				setError(err instanceof Error ? err.message : "An error occurred");
			} finally {
				setLoading(false);
			}
		};

		fetchMessages();
	}, [roomId, limit]);

	return { messages, loading, error };
}
