import { io, Socket } from 'socket.io-client';


export const createSocket = (token: string): Socket => {
  return io('http://localhost:8000', {
    auth: { token },
    autoConnect: false, // Let the provider control when to connect
  });
};

export default createSocket;