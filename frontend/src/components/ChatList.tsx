import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts';
import { useSocketContext } from '../contexts/socket/socketContext';
import { useFetchMessages } from '../hooks/useFetchMessages';
import { userApi } from '../services/api';
import type { User } from '../types';
import type { ChatMessageType } from '../types/chatMessageType';
import ChatMessage from './ChatMessage';
import ChatInput from './LexicalChatInput'

interface ChatListProps {
	roomName: string;
	roomId: string;
}

type EnrichedUser = User & { display_name?: string; profile_picture_url?: string };

const ChatList: React.FC<ChatListProps> = ({ roomName, roomId }: ChatListProps) => {
	const { socket, isConnected } = useSocketContext();
	const { user } = useAuth();
	const currentUserId = user?.id ?? '';
	const { messages: initialMessages, loading, error } = useFetchMessages(roomId, 50);
	const [messages, setMessages] = useState<ChatMessageType[]>([]);
	const [userMap, setUserMap] = useState<Record<string, EnrichedUser>>({});
	const messagesEndRef = useRef<HTMLDivElement>(null);


	// Initialize messages from backend fetch
	useEffect(() => {
		console.log('Initial messages fetched:', initialMessages);
		const mapped = initialMessages.map(
			(msg: ChatMessageType): ChatMessageType => ({
				id: msg.id,
				sender_id: msg.sender_id,
				room_id: msg.room_id,
				content: msg.content,
				created_at: msg.created_at,
				updated_at: msg.updated_at,
				is_edited: msg.is_edited,
				has_emoji: false,
			})
		);
		setMessages(mapped);
	}, [initialMessages]);

	// Fetch user info for all unique sender_ids
	useEffect(() => {
		const uniqueSenderIds = Array.from(new Set(messages.map((msg) => msg.sender_id)));
		if (uniqueSenderIds.length === 0) return;
		userApi.getUsersByIds(uniqueSenderIds).then((users: EnrichedUser[]) => {
			console.log('🚀 ~ users from API:', users);
			const map: Record<string, EnrichedUser> = {};
			users.forEach((u) => {
				const key = 'id' in u && typeof u.id === 'string' ? u.id : u.userId;
				if (key) map[key] = u;
			});
			setUserMap(map);
		});
	}, [messages]);

	// Scroll to bottom whenever messages change
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	});

	// Join/leave room and listen for incoming messages
	useEffect(() => {
		if (!socket) return;
		socket.emit('join', { room: roomId });
		const handleIncomingMessage = (data: ChatMessageType) => {
			console.log('Received message:chat', data);
			if (data.room_id !== roomId) return; // Ignore messages not for this room
			setMessages((prev) => {
				if (prev.some((msg) => msg.id === data.id)) return prev;
				return [...prev, data];
			});
		};
		socket.on('chat:message', handleIncomingMessage);
		return () => {
			if (!socket) return;
			socket.off('chat:message', handleIncomingMessage);
		};
	}, [socket, roomId]);

	return (
		<div className='flex flex-col h-[600px] bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden'>
			{/* Chat Header */}
			<div className='p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm'>
				<h2 className='text-lg font-semibold text-gray-800 dark:text-gray-100'>{roomName ? roomName : "General"} Chat</h2>
				{/* Connection status indicator */}
				<div className='flex items-center'>
					<div
						className={`h-2 w-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
					/>
					<span className='text-sm text-gray-700 dark:text-gray-300'>
						{isConnected ? 'Connected' : 'Disconnected'}
					</span>
				</div>
			</div>

			{/* Messages Container */}
			<div className='flex-1 p-4 overflow-y-auto bg-gray-50 dark:bg-gray-900 rounded-none'>
				{loading ? (
					<div className='flex items-center justify-center h-full'>
						<p className='text-gray-500 dark:text-gray-400'>Loading messages...</p>
					</div>
				) : error ? (
					<div className='flex items-center justify-center h-full'>
						<p className='text-red-500 dark:text-red-400'>Error: {error}</p>
					</div>
				) : messages.length === 0 ? (
					<div className='flex items-center justify-center h-full'>
						<p className='text-gray-500 dark:text-gray-400'>No messages yet</p>
					</div>
				) : (
					<div className='space-y-4'>
						{messages.map((message) => {
							const user = userMap[message.sender_id];
							const author = user
								? {
									id: user.userId,
									username: user.username || 'Unknown User',
									...(user.display_name ? { display_name: user.display_name } : {}),
									...(user.profile_picture_url
										? { profile_picture_url: user.profile_picture_url }
										: {}),
								}
								: {
									id: message.sender_id,
									username: 'Unknown User',
								};
							return (
								<ChatMessage
									key={message.id}
									message={message}
									author={author}
									isCurrentUser={message.sender_id === currentUserId}
								/>
							);
						})}
						<div ref={messagesEndRef} />
					</div>
				)}
			</div>

			{/* Message Input */}
			<div className='p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 rounded-b-lg'>
				<ChatInput roomId={roomId} senderId={currentUserId} />
			</div>
		</div>
	);
};

export default ChatList;
