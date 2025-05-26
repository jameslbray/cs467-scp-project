export interface UserStatusType {
	user_id: string;
	username?: string;
	status: 'online' | 'away' | 'busy' | 'offline';
	last_status_change: string;
}