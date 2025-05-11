import { useState, useEffect } from "react";

export interface Message {
    _id: string;
    room_id: string;
    sender_id: string;
    content: string;
    timestamp: string;
}

export function useFetchMessages(roomId: string, limit = 50) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!roomId) {
            setLoading(true);
            setError("Room ID is required");
            return;
        }

        const token = localStorage.getItem("auth_token");
        if (!token) {
            setLoading(true);
            setError("No auth token found");
            return;
        }

        const fetchMessages = async () => {
            try {
                const response = await fetch(`/api/rooms/${roomId}/messages?limit=${limit}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                    },
                });

                if (!response.ok) {
                    throw new Error("Failed to fetch messages: ${response.statusText}");
                }

                const data = await response.json();
                setMessages(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : "An error occurred");
            } finally {
                setLoading(false);
            }
        };

        fetchMessages();
    }, [roomId, token, limit]);

    return { messages, loading, error };
}
