import React, { useEffect, useState } from "react";
import { Socket } from "socket.io-client";
import UserStatus from "../components/UserStatus";
import ChatList, { Message } from "../components/ChatList";
import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";
import { useTheme, useAuth } from "../contexts";
import { User, UserStatusIntf } from "../App";
import { ServerEvents } from "../types/serverEvents";
import { getConversationRoomName } from "../utils/roomUtils";
import {
  getSocket,
  disconnectSocket,
  joinRoom,
  sendMessage as sendSocketMessage,
} from "../utils/socketUtils";

// Extended interface that includes username
interface FriendWithStatus extends UserStatusIntf {
  username: string;
}

// Get socket URL from environment or use default
const socketUrl = import.meta.env.VITE_SOCKET_URL || "http://localhost:8000";

// Custom hook for socket connection
const useSocketConnection = (currentUser: User | null) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [friends, setFriends] = useState<Record<string, FriendWithStatus>>(
    () => {
      // Initialize with self if currentUser exists
      if (currentUser) {
        return {
          [currentUser.id]: {
            user_id: currentUser.id,
            username: `${currentUser.username} (You)`,
            status: "online",
            last_changed: new Date().toISOString(),
          } as FriendWithStatus,
        };
      }
      return {};
    },
  );
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    if (!currentUser) return;

    // Track socket connection with a ref to avoid closure issues
    const socketRef = { current: null as Socket | null };

    const initializeSocket = () => {
      try {
        // Initialize socket connection with our utility
        const authToken = localStorage.getItem("auth_token") || "";
        console.log(`Initializing socket connection to ${socketUrl}`);

        // Use a definite assignment to handle the socket
        const newSocket = getSocket(socketUrl, authToken);

        // Verify socket was created properly
        if (!newSocket) {
          console.error(
            "Failed to create socket connection - getSocket returned null/undefined",
          );
          setIsConnected(false);
          return;
        }

        // Store the socket connection in both state and ref
        socketRef.current = newSocket;
        setSocket(newSocket);

        // Set up connect event
        newSocket.on("connect", () => {
          console.log("Connected to SycoLibre socket server");
          setIsConnected(true);

          // Request friend statuses
          newSocket.emit(ServerEvents.REQUEST_STATUSES, {});

          // Join self-chat room automatically
          const selfRoom = getConversationRoomName(
            currentUser.id,
            currentUser.id,
          );
          const joined = joinRoom(selfRoom);
          if (joined) {
            console.log(`Joined self-chat room: ${selfRoom}`);
          } else {
            console.warn(
              `Failed to join self-chat room: ${selfRoom}. Will retry later.`,
            );
            // Schedule retry
            setTimeout(() => joinRoom(selfRoom), 3000);
          }
        });

        newSocket.on("disconnect", (reason) => {
          console.log(`Disconnected from SycoLibre socket server: ${reason}`);
          setIsConnected(false);
        });

        newSocket.on("connect_error", (error) => {
          console.error(`Socket connection error: ${error.message}`);
          setIsConnected(false);
        });

        newSocket.on(
          ServerEvents.FRIEND_STATUSES,
          (data: { statuses: Record<string, FriendWithStatus> }) => {
            console.log("Received friend statuses:", data.statuses);

            if (!currentUser) return;

            // Always ensure self is included in the friends list
            const friendsWithSelf = {
              ...data.statuses,
              [currentUser.id]: {
                user_id: currentUser.id,
                username: `${currentUser.username} (You)`,
                status: "online",
                last_changed: new Date().toISOString(),
              } as FriendWithStatus,
            };

            console.log("Setting friends with self included:", friendsWithSelf);
            console.log("Self user ID:", currentUser.id);
            setFriends(friendsWithSelf);
          },
        );

        newSocket.on(
          ServerEvents.FRIEND_STATUS_CHANGED,
          (data: FriendWithStatus) => {
            console.log(
              "Friend status changed for:",
              data.user_id,
              data.username,
            );

            setFriends((prev) => {
              const updated = {
                ...prev,
                [data.user_id]: data,
              };

              // Always ensure self is in the list
              if (!updated[currentUser.id]) {
                updated[currentUser.id] = {
                  user_id: currentUser.id,
                  username: `${currentUser.username} (You)`,
                  status: "online",
                  last_changed: new Date().toISOString(),
                } as FriendWithStatus;
                console.log("Re-added self to friends list during update");
              }

              return updated;
            });
          },
        );

        newSocket.on(ServerEvents.MESSAGE, (message: Message) => {
          console.log("Received message:", message);
          setMessages((prev) => [...prev, message]);
        });
      } catch (error) {
        console.error("Error initializing socket connection:", error);
        setIsConnected(false);
      }
    };

    // Initialize the socket
    initializeSocket();

    // Cleanup function
    return () => {
      console.log("Cleaning up socket connection...");

      // Use the ref for cleanup to avoid null issues
      if (socketRef.current) {
        console.log("Removing listeners and disconnecting socket...");
        try {
          socketRef.current.removeAllListeners();
          socketRef.current.disconnect();
        } catch (err) {
          console.error("Error during socket cleanup:", err);
        }
      }

      // Also call the utility disconnect function for completeness
      disconnectSocket();
    };
  }, [currentUser]); // currentUser is the only dependency we need

  // Function to send a message
  const sendMessage = async (
    recipientId: string,
    content: string,
  ): Promise<boolean> => {
    if (!currentUser) {
      console.warn("Cannot send message: No current user");
      return false;
    }

    if (!isConnected) {
      console.warn("Cannot send message: Socket not connected");
      return false;
    }

    if (!socket) {
      console.warn("Cannot send message: Socket instance is null");
      return false;
    }

    try {
      const roomName = getConversationRoomName(currentUser.id, recipientId);
      console.log(`Sending message to room: ${roomName}`);

      // Join the room first if needed
      const joined = joinRoom(roomName);
      if (!joined) {
        console.warn(`Failed to join room: ${roomName}`);
        return false;
      }

      // Send the message using our utility
      return await sendSocketMessage(
        recipientId,
        content,
        currentUser.username,
        roomName,
      ).catch((err) => {
        console.error("Error sending message:", err);
        return false;
      });
    } catch (error) {
      console.error("Unexpected error sending message:", error);
      return false;
    }
  };

  return {
    socket,
    friends,
    isConnected,
    messages,
    sendMessage,
  };
};

const ChatPage: React.FC = () => {
  const { darkMode, toggleDarkMode } = useTheme();
  const { user, logout } = useAuth();
  const { friends, isConnected, messages, sendMessage } =
    useSocketConnection(user);
  const [friendCount, setFriendCount] = useState(0);

  // Update friend count when friends change
  useEffect(() => {
    // Subtract 1 to not count yourself in the friend count display
    const actualFriendCount = Math.max(0, Object.keys(friends).length - 1);
    setFriendCount(actualFriendCount);
  }, [friends]);

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200`}
    >
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <UserStatus />
              {/* Self-chat indicator */}
              {user && friends[user.id] && (
                <div className="ml-4 px-2 py-1 text-sm text-white bg-green-600 rounded-md">
                  Self-chat Ready
                </div>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none"
                aria-label={
                  darkMode ? "Switch to light mode" : "Switch to dark mode"
                }
              >
                {darkMode ? (
                  <SunIcon className="h-6 w-6" />
                ) : (
                  <MoonIcon className="h-6 w-6" />
                )}
              </button>

              <div className="flex items-center">
                <div
                  className={`h-2 w-2 rounded-full mr-2 ${
                    isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
                  }`}
                ></div>
                <span
                  className={`text-sm ${
                    isConnected
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {isConnected ? "Connected" : "Disconnected"}
                </span>
              </div>

              <div className="text-sm text-gray-700 dark:text-gray-300">
                {friendCount} {friendCount === 1 ? "friend" : "friends"} online
              </div>

              <button
                onClick={logout}
                className="ml-4 px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Chat Options</h2>
              <div className="space-y-2">
                {Object.values(friends).map((friend) => (
                  <button
                    key={friend.user_id}
                    onClick={() => {
                      if (sendMessage) {
                        sendMessage(friend.user_id, "Hello!");
                      }
                    }}
                    className="w-full text-left px-4 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {friend.username}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <ChatList
              messages={messages}
              sendMessage={sendMessage}
              friends={friends}
              currentUser={user}
              isConnected={isConnected}
            />
          </div>
        </div>

        {/* Debug Button */}
        <button
          onClick={() => {
            console.log("Friends object:", friends);
            console.log("Current user:", user);
            console.log("Friends keys:", Object.keys(friends));
            if (user) {
              console.log("Is self in friends?", !!friends[user.id]);
              console.log("Self user ID:", user.id);
            }
          }}
          className="mt-4 px-3 py-1 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none"
        >
          Debug Friends List
        </button>
      </main>
    </div>
  );
};

export default ChatPage;
