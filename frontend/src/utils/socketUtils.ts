import { io, Socket } from "socket.io-client";
import { ServerEvents } from "../types/serverEvents";

// Track the socket instance
let socketInstance: Socket | null = null;
let reconnectionAttemptCount = 0;

// Default socket URL as fallback
const DEFAULT_SOCKET_URL = "http://localhost:8000";

// Socket connection options
const socketOptions = {
  autoConnect: false,
  reconnection: true,
  reconnectionAttempts: 20,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 10000,
  timeout: 30000,
  transports: ["websocket", "polling"],
  withCredentials: true,
  path: '/socket.io/'
};

/**
 * Initialize the socket connection
 * @param url The socket server URL
 * @param authToken The authentication token
 * @returns The socket instance
 */
export const initializeSocket = (url: string, authToken: string): Socket => {
  // Validate token before attempting connection
  if (!authToken || authToken.trim() === "") {
    console.error("No authentication token provided. Please log in again.");
  }

  // If already connected, return the existing instance
  if (socketInstance?.connected) {
    console.log("Using existing socket connection");
    return socketInstance;
  }

  // Clean up any existing instance
  if (socketInstance) {
    console.log("Cleaning up existing socket instance");
    socketInstance.removeAllListeners();
    socketInstance.disconnect();
    socketInstance = null;
  }

  // Validate URL
  const validatedUrl = validateSocketUrl(url);

  try {
    // Log minimal token info for debugging (first few chars only)
    console.log(`Authenticating with token: ${authToken.substring(0, 10)}...`);

    // Prepare connection options with authentication
    // Send token in all possible ways for maximum compatibility
    const connectionOptions = {
      ...socketOptions,
      auth: { token: authToken },
      query: { token: authToken }
    };

    // Create new socket instance
    console.log(`Connecting to socket server at: ${validatedUrl}`);
    socketInstance = io(validatedUrl, connectionOptions);

    // Set up event listeners
    socketInstance.on("connect", () => {
      console.log("Socket connection established");
      reconnectionAttemptCount = 0;
    });

    socketInstance.on("connect_error", (error) => {
      console.error("Socket connection error:", error.message);

      // Provide specific error diagnostics
      if (error.message.includes("CORS")) {
        console.error(
          "CORS error detected. Please check server CORS configuration.",
        );
      } else if (error.message.includes("xhr poll error")) {
        console.error("XHR polling error. Server might be unavailable.");
      } else if (error.message.includes("websocket error")) {
        console.error("WebSocket error. Falling back to polling transport.");
        if (socketInstance) {
          socketInstance.io.opts.transports = ["polling"];
        }
      } else if (error.message.includes("not authorized")) {
        console.error(
          "Authentication error. Your token may be invalid or expired.",
        );
        console.error(
          "Try logging out and back in to refresh your authentication token.",
        );
      } else if (error.message.includes("Bad request")) {
        console.error(
          "Bad request error. Token may be in incorrect format or missing.",
        );
        console.error(`Token length: ${authToken.length}, format: JWT`);
      }

      // Handle reconnection
      reconnectionAttemptCount++;
      const backoffDelay = Math.min(
        2000 * Math.pow(1.5, Math.min(reconnectionAttemptCount, 10)),
        20000,
      );
      console.log(
        `Will attempt reconnection in ${(backoffDelay / 1000).toFixed(1)} seconds...`,
      );

      setTimeout(() => {
        if (socketInstance) {
          console.log("Attempting to reconnect after connection error...");
          socketInstance.connect();
        }
      }, backoffDelay);
    });

    socketInstance.on("disconnect", (reason) => {
      console.log(`Socket disconnected: ${reason}`);
    });

    socketInstance.on("error", (error) => {
      console.error("Socket error:", error);
    });

    // Connect to the server
    socketInstance.connect();
    return socketInstance;
  } catch (error) {
    console.error("Failed to initialize socket:", error);
    reconnectionAttemptCount = 0;

    // Return a dummy socket instance to prevent errors
    socketInstance = io(validatedUrl, { autoConnect: false });
    return socketInstance;
  }
};

/**
 * Get the current socket instance or initialize a new one
 * @param url The socket server URL
 * @param authToken The authentication token
 * @returns The socket instance
 */
export const getSocket = (url: string, authToken: string): Socket => {
  if (!socketInstance) {
    return initializeSocket(url, authToken);
  }
  return socketInstance;
};

/**
 * Disconnect the socket
 */
export const disconnectSocket = (): void => {
  if (socketInstance) {
    socketInstance.disconnect();
    socketInstance = null;
    console.log("Socket disconnected and instance cleared");
  }
};

/**
 * Emit an event through the socket
 * @param event The event name
 * @param data The event data
 * @returns True if successfully emitted, false otherwise
 */
export const emitEvent = <T>(event: string, data: T): boolean => {
  if (socketInstance?.connected) {
    socketInstance.emit(event, data);
    return true;
  } else {
    console.error(`Cannot emit event: Socket not connected`);
    return false;
  }
};

/**
 * Join a room
 * @param room The room to join
 * @returns True if successfully joined, false otherwise
 */
export const joinRoom = (room: string): boolean => {
  if (socketInstance?.connected) {
    socketInstance.emit("join_room", { room });
    console.log(`Joined room: ${room}`);
    return true;
  } else {
    console.error(`Cannot join room ${room}: Socket not connected`);
    return false;
  }
};

/**
 * Send a message
 * @param recipientId The recipient ID
 * @param content The message content
 * @param senderName The sender name
 * @param roomName The room name
 * @returns Promise that resolves to true if successfully sent, false otherwise
 */
export const sendMessage = (
  recipientId: string,
  content: string,
  senderName: string,
  roomName: string,
): Promise<boolean> => {
  return new Promise((resolve) => {
    if (!socketInstance) {
      console.error("Cannot send message: Socket instance not created");
      resolve(false);
      return;
    }

    if (!socketInstance.connected) {
      console.warn(
        "Socket not connected, attempting to connect before sending...",
      );
      socketInstance.connect();

      // Set a timeout in case connection takes too long
      const timeout = setTimeout(() => {
        console.error(
          "Socket connection timed out when trying to send message",
        );
        resolve(false);
      }, 5000);

      // Listen for connection and then send
      socketInstance.once("connect", () => {
        clearTimeout(timeout);
        const messageData = {
          recipientId,
          content,
          timestamp: new Date(),
          senderName,
          roomName,
        };

        socketInstance?.emit(ServerEvents.MESSAGE, messageData);
        console.log("Message sent after reconnection");
        resolve(true);
      });

      return;
    }

    // We're already connected, send immediately
    const messageData = {
      recipientId,
      content,
      timestamp: new Date(),
      senderName,
      roomName,
    };

    socketInstance.emit(ServerEvents.MESSAGE, messageData);
    console.log("Message sent");
    resolve(true);
  });
};

/**
 * Validate and normalize the socket URL
 * @param url The socket URL to validate
 * @returns The validated URL
 */
function validateSocketUrl(url: string): string {
  // Extract socket URL from environment variables if available
  const envSocketUrl = import.meta.env.VITE_SOCKET_URL;

  // Use provided URL, environment variable, or fallback in that order
  const sourceUrl = url || envSocketUrl || DEFAULT_SOCKET_URL;

  if (!url) {
    console.warn(`Socket URL is empty, using ${sourceUrl}`);
  }

  try {
    // Test if it's a valid URL
    new URL(sourceUrl);

    // Remove any trailing slashes or socket.io paths
    let cleanUrl = sourceUrl.replace(/\/socket\.io\/?.*$/, "");
    cleanUrl = cleanUrl.replace(/\/$/, "");

    // Check for protocol - ensure we're using http/https
    if (!cleanUrl.startsWith("http://") && !cleanUrl.startsWith("https://")) {
      cleanUrl = `http://${cleanUrl}`;
      console.warn(`Added http:// protocol to URL: ${cleanUrl}`);
    }

    console.log(`Normalized socket URL: ${cleanUrl}`);
    return cleanUrl;
  } catch (error) {
    console.error(`Invalid socket URL: ${sourceUrl}, error: ${error}`);

    // Try to detect if it might be a hostname without protocol
    if (sourceUrl && !sourceUrl.includes("://") && !sourceUrl.startsWith("/")) {
      const urlWithProtocol = `http://${sourceUrl}`;
      try {
        new URL(urlWithProtocol);
        console.log(
          `Recovered invalid URL by adding protocol: ${urlWithProtocol}`,
        );
        return urlWithProtocol;
      } catch (e) {
        console.error(
          `Failed to recover URL with protocol: ${urlWithProtocol}, error: ${e}`,
        );
      }
    }

    return DEFAULT_SOCKET_URL; // Use default fallback
  }
}
