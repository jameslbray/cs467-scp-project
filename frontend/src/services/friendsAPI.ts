import { userApi } from '../services/api';
import { FriendConnection } from '../types/friendsTypes';

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
