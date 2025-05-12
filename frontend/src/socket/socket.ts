import { type Socket, io } from "socket.io-client";

let socket: Socket | null = null;

export function getSocket(token: string) {
	if (!socket) {
		socket = io("http://localhost:8000", {
			auth: { token: token },
		});
	}
	return socket;
}

export function disconnectSocket() {
	if (socket) {
		socket.disconnect();
		socket = null;
	}
}
