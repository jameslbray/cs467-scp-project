export interface ChatMessageType {
	id: string;
	sender_id: string;
	room_id: string;
	content: string;
	created_at: string; // ISO string
	updated_at: string; // ISO string
	is_edited: boolean;
	has_emoji?: boolean;
	author?: {
		id: string;
		username: string;
		profilePicture?: string;
	};
	local_time?: string; // ISO string in sender's local time
	timezone_offset?: number; // Minutes offset from UTC (e.g., -420 for PDT)
}
