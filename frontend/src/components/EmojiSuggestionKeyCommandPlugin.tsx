import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { KEY_ENTER_COMMAND } from 'lexical';
import { useEffect, useRef } from 'react';
import { useEmojiSuggestion } from '../contexts/emojiSuggestionContext';

export function EmojiSuggestionKeyCommandPlugin() {
	const [editor] = useLexicalComposerContext();
	const { popupVisible, selectedIndex, suggestions, handleKeyDown } = useEmojiSuggestion();
	const commandRef = useRef<null | (() => void)>(null);

	useEffect(() => {
		// Unregister previous command if any
		if (commandRef.current) {
			commandRef.current();
			commandRef.current = null;
		}
		if (popupVisible && selectedIndex >= 0 && selectedIndex < suggestions.length) {
			commandRef.current = editor.registerCommand(
				KEY_ENTER_COMMAND,
				(event) => {
					event?.preventDefault();
					const fakeEvent = {
						key: 'Enter',
						preventDefault: () => {},
						stopPropagation: () => {},
					} as unknown as React.KeyboardEvent<HTMLDivElement>;
					handleKeyDown(fakeEvent);
					return true;
				},
				1 // high priority
			);
		}
		// Cleanup on unmount
		return () => {
			if (commandRef.current) {
				commandRef.current();
				commandRef.current = null;
			}
		};
	}, [editor, popupVisible, suggestions, selectedIndex, handleKeyDown]);

	return null;
}
