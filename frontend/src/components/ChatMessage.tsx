import { formatDistanceToNow } from 'date-fns';
import type React from 'react';
import type { ChatMessageType } from '../types/chatMessageType';
import { MessageDisplay } from './MessageDisplay';

// Define the props interface for message data
interface ChatMessageProps {
	message: ChatMessageType;
	isCurrentUser?: boolean;
	author?: {
		id: string;
		username: string;
		display_name?: string;
		profile_picture_url?: string;
	};
}
const ChatMessage: React.FC<ChatMessageProps> = ({ message, isCurrentUser = false, author }) => {
	const timeAgo = !Number.isNaN(new Date(message.created_at).getTime())
		? formatDistanceToNow(new Date(message.created_at), {
				addSuffix: true,
		  })
		: 'Invalid date';
	const displayName = author?.display_name || author?.username;
	const profilePicture = author?.profile_picture_url;
	return (
		<div className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'} mb-4`}>
			<div
				className={`${
					isCurrentUser ? 'bg-primary-100 dark:bg-primary-900' : 'bg-gray-100 dark:bg-gray-800'
				} rounded-lg px-4 py-2 max-w-[80%] shadow`}
			>
				{/* Message header with author info and timestamp */}
				<div className='flex items-center mb-1'>
					{!isCurrentUser && (
						<div className='flex items-center'>
							{profilePicture ? (
								<img src={profilePicture} alt={displayName} className='w-8 h-8 rounded-full mr-2' />
							) : (
								<div className='w-8 h-8 rounded-full bg-secondary-500 flex items-center justify-center text-white mr-2'>
									{displayName?.charAt(0).toUpperCase()}
								</div>
							)}
							<span className='font-medium text-gray-900 dark:text-gray-100'>{displayName}</span>
						</div>
					)}
					<span className='text-xs text-gray-500 dark:text-gray-400 ml-auto'>{timeAgo}</span>
				</div>

				{/* Message content with markdown support */}
				<div className='prose dark:prose-dark prose-sm max-w-none'>
					<MessageDisplay message={message.content} />
				</div>
			</div>
		</div>
	);
};

export default ChatMessage;
