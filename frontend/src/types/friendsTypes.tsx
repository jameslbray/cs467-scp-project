export interface FriendConnection {
	id: string;
	user_id: string;
	friend_id: string;
	status: string;
	last_status_change: string;
	userUsername?: string | undefined;
	friendUsername?: string | undefined;
}