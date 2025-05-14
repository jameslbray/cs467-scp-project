// src/hooks/useFetchRooms.ts
import { useEffect, useState } from "react";

export interface Room {
	_id: string;
	name: string;
	members: string[];
}

export function useFetchRooms() {
	const [rooms, setRooms] = useState<Room[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const token = localStorage.getItem("auth_token");
		if (!token) {
			setError("No auth token found");
			setLoading(false);
			return;
		}

		const fetchRooms = async () => {
			try {
				const response = await fetch("http://localhost:8004/rooms", {
					headers: { Authorization: `Bearer ${token}` },
				});
				if (!response.ok) {
					throw new Error(`Failed to fetch rooms: ${response.statusText}`);
				}
				const data = await response.json();
				setRooms(data);
			} catch (err) {
				setError(err instanceof Error ? err.message : "An error occurred");
			} finally {
				setLoading(false);
			}
		};

		fetchRooms();
	}, []);

	return { rooms, loading, error };
}
