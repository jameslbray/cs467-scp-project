import React, { createContext, useContext } from 'react';
import { EmojiMartEmoji } from '../utils/emojiUtils';

interface EmojiSuggestionContextType {
	active: boolean;
	suggestions: EmojiMartEmoji[];
	selectedIndex: number;
	handleKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => boolean;
	popupVisible: boolean;
	justInsertedEmoji: React.MutableRefObject<boolean>;
}

const EmojiSuggestionContext = createContext<EmojiSuggestionContextType | undefined>(undefined);

export function useEmojiSuggestion() {
	const ctx = useContext(EmojiSuggestionContext);
	if (!ctx) throw new Error('useEmojiSuggestion must be used within EmojiSuggestionProvider');
	return ctx;
}

export { EmojiSuggestionContext };
