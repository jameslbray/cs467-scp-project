export interface UserStatusType {
	user_id: string;
	username?: string;
	status: 'online' | 'away' | 'offline';
	last_changed: string;
}