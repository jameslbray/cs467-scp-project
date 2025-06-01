import data from '@emoji-mart/data';
import Picker from '@emoji-mart/react';
import { CodeNode } from '@lexical/code';
import { LinkNode } from '@lexical/link';
import { ListItemNode, ListNode } from '@lexical/list';
import { $convertToMarkdownString, TRANSFORMERS } from '@lexical/markdown';
import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { MarkdownShortcutPlugin } from '@lexical/react/LexicalMarkdownShortcutPlugin';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin';
import { HeadingNode, QuoteNode } from '@lexical/rich-text';
import {
	$createTextNode,
	$getRoot,
	$getSelection,
	EditorState,
	LexicalNode,
	TextNode,
} from 'lexical';
import React, { useEffect, useRef, useState } from 'react';
import type { Socket } from 'socket.io-client';
import { v4 as uuidv4 } from 'uuid';
import { useEmojiSuggestion } from '../contexts/emojiSuggestionContext';
import { useSocketContext } from '../contexts/socket/socketContext';
import type { ChatMessageType } from '../types/chatMessageType';
import { findEmojiByShortcode } from '../utils/emojiUtils';
import { $createEmojiNode, EmojiNode } from './EmojiNode';
import { EmojiSuggestionKeyCommandPlugin } from './EmojiSuggestionKeyCommandPlugin';
import { EmojiSuggestionProvider } from './EmojiSuggestionPlugin';

interface ChatInputProps {
	roomId: string;
	senderId: string;
	onSend?: (message: ChatMessageType) => void;
}

function LexicalEditorInner({
	roomId,
	senderId,
	onSend,
	contentEditableRef,
	socket,
}: {
	roomId: string;
	senderId: string;
	onSend: (message: ChatMessageType) => void;
	contentEditableRef: React.RefObject<HTMLDivElement | null>;
	socket: Socket;
}) {
	const [editor] = useLexicalComposerContext();
	const [showEmojiPicker, setShowEmojiPicker] = useState(false);
	const [message, setMessage] = useState('');
	const { handleKeyDown, justInsertedEmoji } = useEmojiSuggestion();

	function replaceShortcodesWithEmoji(text: string): string {
		return text.replace(/:([a-zA-Z0-9_+-]+):/g, (match, p1) => {
			const emoji = findEmojiByShortcode(p1);
			return emoji || match;
		});
	}

	useEffect(() => {
		function handleEsc(e: KeyboardEvent) {
			if (e.key === 'Escape') setShowEmojiPicker(false);
		}
		window.addEventListener('keydown', handleEsc);
		return () => window.removeEventListener('keydown', handleEsc);
	}, []);

	function onChange(editorState: EditorState) {
		editorState.read(() => {
			const text = $getRoot().getTextContent();
			setMessage(text);
			if (showEmojiPicker) setShowEmojiPicker(false); // Hide picker on typing
		});
	}

	function handleSend() {
		if (!message.trim()) return;
		const now = new Date().toISOString();
		let markdown = '';
		editor.update(() => {
			markdown = $convertToMarkdownString(TRANSFORMERS);
			$getRoot().clear();
		});
		// Replace :shortcode: with emoji
		const contentWithEmojis = replaceShortcodesWithEmoji(markdown);
		const msg: ChatMessageType = {
			id: uuidv4(),
			sender_id: senderId,
			room_id: roomId,
			content: contentWithEmojis,
			created_at: now,
			updated_at: now,
			is_edited: false,
			has_emoji: /\p{Emoji}/u.test(contentWithEmojis),
		};
		socket.emit('chat_message', msg);
		if (onSend) onSend(msg);
		setMessage('');
	}

	function handleEditorKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
		if (handleKeyDown(e)) return;

		if (justInsertedEmoji.current) {
			justInsertedEmoji.current = false;
			e.preventDefault();
			return;
		}

		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
			return;
		}
	}

	function handleEmojiSelect(emoji: { native: string }) {
		editor.update(() => {
			const selection = $getSelection();
			if (selection && selection.insertText) {
				selection.insertText(emoji.native);
			}
		});
		setShowEmojiPicker(false);
		contentEditableRef.current?.focus();
	}

	return (
		<>
			<RichTextPlugin
				contentEditable={
					<ContentEditable
						ref={contentEditableRef}
						className='flex-grow border px-4 py-2 rounded shadow resize-none min-h-[3em] max-h-40 overflow-y-auto bg-white focus:outline-none relative'
						onKeyDown={handleEditorKeyDown}
						aria-label='Type a message with markdown and emojis...'
						style={{
							position: 'relative',
							background: 'transparent',
							caretColor: '#111',
							zIndex: 2,
						}}
					/>
				}
				placeholder={
					<div
						className='absolute left-4 top-2 text-gray-400 pointer-events-none select-none'
						style={{ zIndex: 1 }}
					>
						Type a message with markdown and emojis...
					</div>
				}
				ErrorBoundary={LexicalErrorBoundary}
			/>
			<MarkdownShortcutPlugin transformers={TRANSFORMERS} />
			<HistoryPlugin />
			<OnChangePlugin onChange={onChange} />
			<button
				type='button'
				onClick={() => setShowEmojiPicker((v) => !v)}
				className='px-2 py-1 rounded border bg-white hover:bg-gray-100'
				style={{ position: 'relative' }}
			>
				😊
			</button>
			<div className='relative'>
				{showEmojiPicker && (
					<div className='absolute bottom-full right-0 z-50'>
						<Picker data={data} onEmojiSelect={handleEmojiSelect} />
					</div>
				)}
			</div>
			<button
				type='button'
				onClick={handleSend}
				className='bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 ml-2'
			>
				Send
			</button>
		</>
	);
}

// Plugin: Replace :shortcode: with emoji live in the editor
function EmojiShortcodeTransformPlugin() {
	const [editor] = useLexicalComposerContext();
	useEffect(() => {
		return editor.registerNodeTransform(TextNode, (node: TextNode) => {
			const text: string = node.getTextContent();
			const regex = /:([a-zA-Z0-9_+-]+):/g;
			let match;
			let replaced = false;
			let lastIndex = 0;
			const newNodes: (TextNode | EmojiNode)[] = [];
			while ((match = regex.exec(text)) !== null) {
				const [full, shortcodeRaw] = match;
				const shortcode = typeof shortcodeRaw === 'string' ? shortcodeRaw : '';
				const emoji = shortcode ? findEmojiByShortcode(shortcode) : undefined;
				if (emoji && shortcode) {
					const before = text.slice(lastIndex, match.index);
					if (before.length > 0) {
						newNodes.push($createTextNode(before));
					}
					newNodes.push($createEmojiNode(shortcode));
					lastIndex = match.index + full.length;
					replaced = true;
				}
			}
			if (replaced) {
				const after = text.slice(lastIndex);
				if (after.length > 0) {
					newNodes.push($createTextNode(after));
				}
				if (newNodes.length === 1) {
					node.replace(newNodes[0]!);
				} else if (newNodes.length > 1) {
					let prev: LexicalNode = node.replace(newNodes[0]!);
					for (let i = 1; i < newNodes.length; i++) {
						prev = prev.insertAfter(newNodes[i]!);
					}
				}
			}
		});
	}, [editor]);
	return null;
}

export default function ChatInput({ roomId, senderId, onSend }: ChatInputProps) {
	const { socket } = useSocketContext();
	const contentEditableRef = useRef<HTMLDivElement | null>(null);

	if (!socket) return null;

	return (
		<div className='flex flex-col gap-2 mt-4 relative'>
			<div className='flex gap-2 items-center'>
				<LexicalComposer
					initialConfig={{
						namespace: 'ChatInput',
						theme: {},
						onError(error: Error) {
							throw error;
						},
						nodes: [HeadingNode, QuoteNode, ListNode, ListItemNode, CodeNode, LinkNode, EmojiNode],
					}}
				>
					<EmojiSuggestionProvider>
						<EmojiSuggestionKeyCommandPlugin />
						<LexicalEditorInner
							roomId={roomId}
							senderId={senderId}
							onSend={onSend ?? (() => { })}
							contentEditableRef={contentEditableRef}
							socket={socket}
						/>
						<EmojiShortcodeTransformPlugin />
					</EmojiSuggestionProvider>
				</LexicalComposer>
			</div>
		</div>
	);
}
