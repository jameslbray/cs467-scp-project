import type React from "react";
import type { UserStatusIntf } from "../App";

interface FriendStatusItemProps {
	status: UserStatusIntf;
}

const FriendStatusItem: React.FC<FriendStatusItemProps> = ({ status }) => {
	return (
		<div key={status.user_id}>
			{status.user_id}: {status.status}
		</div>
	);
};

export default FriendStatusItem;