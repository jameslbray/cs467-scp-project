import { useEffect } from 'react';
import { useSocketContext } from './socketContext';

// Generic hook for subscribing to a socket event
export function useSocketEvent<T = unknown>(
  event: string,
  handler: (data: T) => void
) {
  const { socket } = useSocketContext();

  useEffect(() => {
    if (!socket) return;
    socket.on(event, handler);
    return () => {
      socket.off(event, handler);
    };
  }, [socket, event, handler]);
}

// Helper to emit events
export function useSocketEmit() {
  const { socket } = useSocketContext();
  return (event: string, data?: unknown) => {
    if (socket) {
      socket.emit(event, data);
    }
  };
}