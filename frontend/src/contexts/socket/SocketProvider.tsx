import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Socket } from 'socket.io-client';
import { createSocket } from '../../socket/index';
import { useAuth } from '../auth';
import { SocketContext } from './socketContext';

export const SocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  // Log when the SocketProvider is rendered
  console.log("SocketProvider rendered. Token:", token);

  useEffect(() => {
    console.log("SocketProvider useEffect running. Token:", token);
    if (!token) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    // Always disconnect and recreate the socket when the token changes
    if (socketRef.current) {
      socketRef.current.disconnect();
    }
    const socket = createSocket(token);
    socketRef.current = socket;
    socket.connect();

    socket.on('connect', () => {
      console.log('Socket connected');
      setIsConnected(true);
    });
    socket.on('disconnect', () => {
      console.log('Socket disconnected');
      setIsConnected(false);
    });
    socket.on('connect_error', (err) => {
      console.error('Socket connect_error:', err);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.off('connect');
        socketRef.current.off('disconnect');
        socketRef.current.off('connect_error');
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      setIsConnected(false);
    };
  }, [token]);

  // Make sure to include socketRef.current in the context value dependencies
  const contextValue = useMemo(
    () => ({
      socket: socketRef.current,
      isConnected,
    }),
    [isConnected]
  );

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  );
};