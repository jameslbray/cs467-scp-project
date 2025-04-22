import React, { useEffect, useState } from 'react';
import { Socket } from 'socket.io-client'; 

interface Message {
  sender_id: string;
  content: string;
  timestamp: string;
  room_id: string;
}

interface MessageListProps {
  roomId: string;
  socket: Socket; 
}

const MessageList: React.FC<MessageListProps> = ({ roomId, socket }) => {
  const [messages, setMessages] = useState<Message[]>([]);

  const fetchMessages = () => {
    if (socket && socket.connected) {
      console.log('Emitting fetch_recent_messages for room:', roomId);
      socket.emit('fetch_recent_messages', { room_id: roomId });
    } else {
      console.log('Socket not ready to fetch messages');
    }
  };

  useEffect(() => {
    if (!socket) return;

    const handleConnect = () => {
      console.log('Connected to socket for messages');
      socket.emit('join_room', { room: roomId });
      fetchMessages();
    };

    const handleRecentMessages = (data: { messages: Message[] }) => {
      console.log('Received recent messages:', data.messages);
      setMessages(data.messages);
    };

    const handleNewMessage = (newMessage: Message) => {
      console.log('chat_message received:', newMessage);
      if (newMessage.room_id === roomId) {
        fetchMessages();
      }
    };

    socket.on('connect', handleConnect);
    socket.on('recent_messages', handleRecentMessages);
    socket.on('chat_message', handleNewMessage);

    return () => {
      socket.off('connect', handleConnect);
      socket.off('recent_messages', handleRecentMessages);
      socket.off('chat_message', handleNewMessage);
    };
  }, [roomId, socket]);

  return (
    <div style={{ padding: '10px', backgroundColor: '#f5f5f5' }}>
      <h3>Recent Messages in "{roomId}"</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {messages.map((msg, index) => (
          <li key={index} style={{ marginBottom: '10px' }}>
            <strong>{msg.sender_id}</strong>: {msg.content} <br />
            <small>{new Date(msg.timestamp).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default MessageList;
