import React, { useState } from 'react';
import { Socket } from 'socket.io-client';

interface ChatInputProps {
  roomId: string;
  senderId: string;
  recipientIds: string[];
  socket: Socket;
}

const ChatInput: React.FC<ChatInputProps> = ({ roomId, senderId, recipientIds, socket }) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() === '') return;

    const messageData = {
      sender_id: senderId,
      room_id: roomId,
      recipient_ids: recipientIds,
      content: message,
      timestamp: new Date().toISOString(),
      has_emoji: false 
    };

    console.log('Emitting send_message:', messageData);
    socket.emit('send_message', messageData);
    setMessage('');
  };

  return (
    <div className="flex gap-2 items-center mt-4">
      <input
        type="text"
        placeholder="Type a message..."
        className="flex-grow border px-4 py-2 rounded shadow"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
      />
      <button
        onClick={handleSend}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        Send
      </button>
    </div>
  );
};

export default ChatInput;
