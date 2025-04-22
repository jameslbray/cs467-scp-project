// App.tsx or similar component
import React, { useEffect, useState } from 'react';
import UserStatusDropdown from './components/UserStatusDropdown.tsx';
import ChatInput from './components/ChatInput.tsx';
import MessageList from './components/MessageList.tsx';

import { io, Socket } from 'socket.io-client';
import { ServerEvents, UserStatus, User, ClientEvents } from './types';

const socket = io('http://localhost:3001', {
  auth: { userId: '1' },
});

const App: React.FC = () => {
  // const [socket, setSocket] = useState<Socket | null>(null);
  // const [currentUser, setCurrentUser] = useState<User | null>(null);
  // const [friends, setFriends] = useState<Record<string, UserStatus>>({});
  // const [isConnected, setIsConnected] = useState(false);

  // // Fetch current user info (mocked for this example)
  // useEffect(() => {
  //   // Simulating a logged-in user
  //   setCurrentUser({
  //     userId: '1',
  //     username: 'michael_shaffer',
  //     profile_picture_url: './assets/default_profile.png',
  //   });
  // }, []);

  // // Connect to socket server when user is authenticated
  // useEffect(() => {
  //   if (!currentUser) return;

  //   // Initialize socket connection
  //   const socketConnection = io('http://localhost:3001',
  //       {
  //       auth: {
  //         userId: currentUser.userId
  //       }
  //     }
  //   );

  //   setSocket(socketConnection);

  //   // Connection events
  //   socketConnection.on('connect', () => {
  //     console.log('Connected to SycoLibre socket server');
  //     setIsConnected(true);

  //     // Request friend statuses after connection
  //     socketConnection.emit(ClientEvents.REQUEST_FRIEND_STATUSES, {});
  //   });

  //   socketConnection.on('disconnect', () => {
  //     console.log('Disconnected from SycoLibre socket server');
  //     setIsConnected(false);
  //   });

  //   // Handle friend status updates
  //   socketConnection.on(ServerEvents.FRIEND_STATUSES, (data: { statuses: Record<string, UserStatus> }) => {
  //     setFriends(data.statuses);
  //   });

  //   socketConnection.on(ServerEvents.FRIEND_STATUS_CHANGED, (data: UserStatus) => {
  //     setFriends(prev => ({
  //       ...prev,
  //       [data.userId]: data
  //     }));
  //   });

  //   // Clean up connection on unmount
  //   return () => {
  //     socketConnection.disconnect();
  //   };
  // }, [currentUser]);

  // if (!currentUser) {
  //   return <div>Loading...</div>;
  // }
  // The component below also calls all of the same socket events as the one above
  return (
    <div>
      <div>
        <UserStatusDropdown />
      </div>
      <div>
        <MessageList roomId="test-room" socket={socket} />
        <ChatInput roomId="test-room" senderId="1" recipientIds={['2', '3']} socket={socket} />
      </div>
    </div>
  );
};

export default App;