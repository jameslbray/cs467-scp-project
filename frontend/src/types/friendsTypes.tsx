export interface FriendConnection {
	id: string;
	user_id: string;
	friend_id: string;
	status: string;
	userUsername?: string | undefined;
	friendUsername?: string | undefined;
}