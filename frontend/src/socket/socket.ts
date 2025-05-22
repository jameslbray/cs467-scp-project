import { type Socket, io } from 'socket.io-client';

let socket: Socket | null = null;
let currentToken: string | null = null;

export function getSocket(token: string) {
	if (!socket || currentToken !== token) {
		if (socket) {
			socket.disconnect();
		}
		socket = io('http://localhost:8000', {
			auth: { token },
		});
		currentToken = token;
	}
	return socket;
}

export function disconnectSocket() {
	if (socket) {
		socket.disconnect();
		socket = null;
	}
}
