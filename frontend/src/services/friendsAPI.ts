import { userApi } from '../services/api';
import { FriendConnection } from '../types/friendsTypes';

const CONNECT_API_URL = 'http://localhost:8005';

export const fetchUserConnections = async (
	userId: string,
	token: string
): Promise<FriendConnection[]> => {
	try {
		const response = await fetch(`${CONNECT_API_URL}/api/connect/${userId}`, {
			headers: {
				Authorization: `Bearer ${token}`,
			},
		});

		if (!response.ok) {
			throw new Error('Failed to fetch connections');
		}

		return await response.json();
	} catch (error) {
		console.error('Failed to fetch user connections:', error);
		return [];
	}
};

export const fetchAcceptedFriends = async (
	userId: string,
	token: string
): Promise<FriendConnection[]> => {
	try {
		const connections = await fetchUserConnections(userId, token);
		// Filter only accepted connections
		const acceptedConnections = connections.filter((conn) => conn.status === 'accepted');
		// Only one direction will exist after acceptance
		return acceptedConnections;
	} catch (error) {
		console.error('Failed to fetch accepted friends:', error);
		return [];
	}
};

export const enrichConnectionsWithUsernames = async (
	connections: Record<string, FriendConnection>,
	currentUserId: string
): Promise<Record<string, FriendConnection>> => {
	try {
		// Deduplicate and extract unique friend IDs
		const friendIds = new Set<string>();
		const uniqueConnections = new Map<string, FriendConnection>();

		Object.values(connections).forEach((conn) => {
			const friendId = conn.user_id === currentUserId ? conn.friend_id : conn.user_id;

			// Only process each friend once
			if (!friendIds.has(friendId)) {
				friendIds.add(friendId);
				uniqueConnections.set(friendId, conn);
			}
		});

		// Get all user IDs for the API call (including current user for completeness)
		const allUserIds = new Set<string>();
		uniqueConnections.forEach((conn) => {
			allUserIds.add(conn.user_id);
			allUserIds.add(conn.friend_id);
		});

		// Fetch users from user API
		const users = await userApi.getUsersByIds(Array.from(allUserIds));
		const userMap: Map<string, { id: string; username: string }> = new Map(
			(users as { id: string; username: string }[]).map((user) => [user.id, user])
		);

		// Create enriched connections object
		const enrichedConnections: Record<string, FriendConnection> = {};
		Array.from(uniqueConnections.values()).forEach((conn) => {
			const friendId = conn.user_id === currentUserId ? conn.friend_id : conn.user_id;
			enrichedConnections[friendId] = {
				...conn,
				userUsername: userMap.get(conn.user_id)?.username,
				friendUsername: userMap.get(conn.friend_id)?.username,
			};
		});
		return enrichedConnections;
	} catch (error) {
		console.error('Error enriching connections with usernames:', error);
		return connections; // Return original connections if enrichment fails
	}
};
