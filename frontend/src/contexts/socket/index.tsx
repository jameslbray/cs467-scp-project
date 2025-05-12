import type React from "react";
import { useEffect, useMemo, useState } from "react";
import type { Socket } from "socket.io-client";
import { getSocket } from "../../socket/socket";
import { useAuth } from "../auth/authContext";
import { SocketContext } from "./socketContext";

interface SocketProviderProps {
	children: React.ReactNode;
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ children }) => {
	const { token } = useAuth();
	const [isConnected, setIsConnected] = useState(false);
	const [socket, setSocket] = useState<Socket | null>(null);

	useEffect(() => {
		if (!token) {
			setSocket(null);
			setIsConnected(false);
			return;
		}

		const newSocket = getSocket(token);
		setSocket(newSocket);

		const handleConnect = () => {
			console.log("Socket connected");
			setIsConnected(true);
		};

		const handleDisconnect = () => {
			console.log("Socket disconnected");
			setIsConnected(false);
		};

		const handleConnectError = (err: Error) => {
			console.error("Socket connect_error:", err);
		};

		newSocket.on("connect", handleConnect);
		newSocket.on("disconnect", handleDisconnect);
		newSocket.on("connect_error", handleConnectError);

		return () => {
			newSocket.off("connect", handleConnect);
			newSocket.off("disconnect", handleDisconnect);
			newSocket.off("connect_error", handleConnectError);
			newSocket.disconnect();
			setSocket(null);
		};
	}, [token]);

	const contextValue = useMemo(
		() => ({
			socket,
			isConnected,
		}),
		[isConnected, socket],
	);

	return (
		<SocketContext.Provider value={contextValue}>
			{children}
		</SocketContext.Provider>
	);
};
