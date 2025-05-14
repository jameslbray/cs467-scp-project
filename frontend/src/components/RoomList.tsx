// src/components/RoomList.tsx
import type React from "react";
import { type Room, useFetchRooms } from "../hooks/useFetchRooms";

interface RoomListProps {
	onSelectRoom: (room: Room) => void;
}

const RoomList: React.FC<RoomListProps> = ({ onSelectRoom }) => {
	const { rooms, loading, error } = useFetchRooms();

	if (loading) return <div>Loading rooms...</div>;
	if (error) return <div>Error: {error}</div>;

	return (
		<ul>
			{rooms.map((room) => (
				<li key={room._id}>
					<button type="button" onClick={() => onSelectRoom(room)}>
						{room.name}
					</button>
				</li>
			))}
		</ul>
	);
};

export default RoomList;
