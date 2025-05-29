import type React from 'react';
import type { UserStatusType } from '../types/userStatusType';

interface FriendStatusItemProps {
	status: UserStatusType;
}

const FriendStatusItem: React.FC<FriendStatusItemProps> = ({ status }) => {
	return (
		<div key={status.user_id}>
			{status.user_id}: {status.status}
		</div>
	);
};

export default FriendStatusItem;
