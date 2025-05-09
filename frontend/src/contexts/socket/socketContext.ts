import { Socket } from "socket.io-client";
import { createContext, useContext } from "react";

interface SocketContextType {
    socket: Socket | null;
    isConnected: boolean;
  }


export const SocketContext = createContext<SocketContextType | undefined>(undefined);

export const useSocketContext = () => {
    const context = useContext(SocketContext);
    if (!context) {
      throw new Error('useSocketContext must be used within a SocketProvider');
    }
    return context;
  };