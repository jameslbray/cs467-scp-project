import { createContext, useContext } from "react";
import type { Socket } from "socket.io-client";

interface SocketContextType {
    socket: Socket | null;
    isConnected: boolean;
  }


export const SocketContext = createContext<SocketContextType | undefined>(undefined);

export const useSocketContext = () => {
    const context = useContext(SocketContext);
    if (!context) {
		throw new Error("useSocketContext must be used within a SocketProvider");
	}
	return context;
};
