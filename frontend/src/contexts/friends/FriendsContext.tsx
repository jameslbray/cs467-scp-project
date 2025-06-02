import type { ReactNode } from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { enrichConnectionsWithUsernames } from '../../services/friendsAPI';
import type { FriendConnection } from '../../types/friendsTypes';
import { ServerEvents } from '../../types/serverEvents';
import { useAuth } from '../auth/authContext';
import { useSocketContext } from '../socket/socketContext';
import { useSocketEvent } from '../socket/useSocket';

interface FriendsContextType {
	friends: Record<string, FriendConnection>;
	acceptedFriends: Record<string, FriendConnection>;
	pendingRequests: Record<string, FriendConnection>;
	loading: boolean;
	refreshFriends: () => void;
}

const FriendsContext = createContext<FriendsContextType>({
	friends: {},
	acceptedFriends: {},
	pendingRequests: {},
	loading: false,
	refreshFriends: () => {},
});

export const FriendsProvider = ({ children }: { children: ReactNode }) => {
	const { user } = useAuth();
	const { isConnected, socket } = useSocketContext();
	const [friends, setFriends] = useState<Record<string, FriendConnection>>({});
	const [enrichedFriends, setEnrichedFriends] = useState<Record<string, FriendConnection>>({});
	const [loading, setLoading] = useState(false);

	console.log(
		'[FriendsProvider] Mount. isConnected:',
		isConnected,
		'user:',
		user,
		'socket:',
		!!socket
	);

	// Listen for GET_FRIENDS_SUCCESS
	useSocketEvent(
		ServerEvents.GET_FRIENDS_SUCCESS,
		(data: FriendConnection[] | { friends: FriendConnection[] }) => {
			let friendsArray: FriendConnection[] = [];
			if (Array.isArray(data)) {
				friendsArray = data;
			} else if (data && Array.isArray(data.friends)) {
				friendsArray = data.friends;
			}
			console.log('[FriendsProvider] Normalized friends array:', friendsArray);
			setFriends((prev) => {
				const updated: Record<string, FriendConnection> = { ...prev };
				friendsArray.forEach((friend) => {
					if (friend && friend.user_id && user && user.id) {
						const friendId = friend.user_id === user.id ? friend.friend_id : friend.user_id;
						updated[friendId] = friend;
					}
				});
				return updated;
			});
		}
	);
	console.log('[FriendsProvider] Registered GET_FRIENDS_SUCCESS handler');

	// Listen for individual friend status changes (optional, for real-time updates)
	useSocketEvent<FriendConnection>(ServerEvents.FRIEND_STATUS_CHANGED, (data) => {
		console.log('[FriendsProvider] Received FRIEND_STATUS_CHANGED:', data);
		if (data && user && user.id) {
			const friendId = data.user_id === user.id ? data.friend_id : data.user_id;
			setFriends((prev) => ({ ...prev, [friendId]: data }));
		}
	});
	console.log('[FriendsProvider] Registered FRIEND_STATUS_CHANGED handler');

	// Fetch and enrich friends when list changes
	useEffect(() => {
		console.log('[FriendsProvider] useEffect (enrich friends) friends:', friends, 'user:', user);
		const enrich = async () => {
			if (user?.id && Object.keys(friends).length > 0) {
				setLoading(true);
				setEnrichedFriends(friends);
				try {
					const enriched = await enrichConnectionsWithUsernames(friends, user.id);
					console.log('[FriendsProvider] Enriched friends:', enriched);
					setEnrichedFriends(enriched);
				} catch (error) {
					console.log('[FriendsProvider] Error enriching friends:', error);
					setEnrichedFriends(friends);
				} finally {
					setLoading(false);
				}
			} else if (user?.id && Object.keys(friends).length === 0) {
				setEnrichedFriends({});
			}
		};
		enrich();
	}, [friends, user, user?.id]);

	// Fetch friends on connect or when requested
	const refreshFriends = useCallback(() => {
		console.log(
			'[FriendsProvider] refreshFriends called. isConnected:',
			isConnected,
			'user:',
			user,
			'socket:',
			!!socket
		);
		if (isConnected && user && socket) {
			console.log('[FriendsProvider] Emitting GET_FRIENDS', { userId: user.id });
			socket.emit(ServerEvents.GET_FRIENDS, { userId: user.id });
		}
	}, [isConnected, user, socket]);

	useEffect(() => {
		console.log(
			'[FriendsProvider] useEffect (fetch friends) isConnected:',
			isConnected,
			'user:',
			user,
			'socket:',
			!!socket
		);
		if (isConnected && user && socket) {
			refreshFriends();
		}
	}, [isConnected, user, refreshFriends, socket]);

	// Memoized selectors for accepted and pending requests
	const acceptedFriends = useMemo(() => {
		const result: Record<string, FriendConnection> = {};
		Object.entries(enrichedFriends).forEach(([id, conn]) => {
			if (conn.status === 'accepted') {
				result[id] = conn;
			}
		});
		return result;
	}, [enrichedFriends]);

	const pendingRequests = useMemo(() => {
		const result: Record<string, FriendConnection> = {};
		Object.entries(enrichedFriends).forEach(([id, conn]) => {
			if (conn.status === 'pending' && conn.friend_id === user?.id) {
				result[id] = conn;
			}
		});
		return result;
	}, [enrichedFriends, user?.id]);

	return (
		<FriendsContext.Provider
			value={{
				friends: enrichedFriends,
				acceptedFriends,
				pendingRequests,
				loading,
				refreshFriends,
			}}
		>
			{children}
		</FriendsContext.Provider>
	);
};

export const useFriends = () => useContext(FriendsContext);
