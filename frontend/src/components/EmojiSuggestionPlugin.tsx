import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $getSelection, $isRangeSelection, TextNode } from 'lexical';
import React, { useCallback, useEffect, useState } from 'react';
import { EmojiSuggestionContext } from '../contexts/emojiSuggestionContext';
import { EmojiMartEmoji, searchEmojisByShortcode } from '../utils/emojiUtils';
import { EmojiSuggestionPopup } from './EmojiSuggestionPopup';

export const EmojiSuggestionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const [editor] = useLexicalComposerContext();
	const [suggestions, setSuggestions] = useState<EmojiMartEmoji[]>([]);
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [popupPos, setPopupPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
	const [active, setActive] = useState(false);
	const justInsertedRef = React.useRef(false);
	const justInsertedEmoji = React.useRef(false);

	const handleSelect = useCallback(
		(emoji: EmojiMartEmoji) => {
			editor.update(() => {
				const selection = $getSelection();
				if ($isRangeSelection(selection)) {
					const anchorNode = selection.anchor.getNode();
					if (anchorNode instanceof TextNode) {
						const text = anchorNode.getTextContent();
						const match = /:([a-zA-Z0-9_+-]*)$/.exec(text.slice(0, selection.anchor.offset));
						if (match) {
							const start = match.index ?? 0;
							const end = selection.anchor.offset;
							const emojiChar = emoji.skins?.[0]?.native ?? '';
							anchorNode.spliceText(start, end, emojiChar);
							// Move caret to after the inserted emoji
							selection.setTextNodeRange(
								anchorNode,
								start + emojiChar.length,
								anchorNode,
								start + emojiChar.length
							);
						}
					}
				}
			});
			justInsertedRef.current = true;
			justInsertedEmoji.current = true;
			setActive(false);
			setSuggestions([]);
		},
		[editor]
	);

	useEffect(() => {
		return editor.registerUpdateListener(({ editorState }) => {
			editorState.read(() => {
				if (justInsertedRef.current) {
					justInsertedRef.current = false;
					setActive(false);
					setSuggestions([]);
					return;
				}
				const selection = $getSelection();
				if ($isRangeSelection(selection) && selection.anchor.key === selection.focus.key) {
					const anchorNode = selection.anchor.getNode();
					if (anchorNode instanceof TextNode) {
						const text = anchorNode.getTextContent().slice(0, selection.anchor.offset);
						const match = /:([a-zA-Z0-9_+-]*)$/.exec(text);
						if (match) {
							const query = match[1] ?? '';
							const found = searchEmojisByShortcode(query);
							setSuggestions(found);
							setSelectedIndex(0);
							setActive(true);

							const rootElem = editor.getRootElement();
							if (!rootElem) {
								setActive(false);
								setSuggestions([]);
								return;
							}

							const sel = window.getSelection();
							if (sel && sel.rangeCount > 0) {
								const range = sel.getRangeAt(0);
								const rects = range.getClientRects();
								const rect = rects.length > 0 ? rects[0] : null;
								const containerRect = rootElem.getBoundingClientRect();
								if (rect) {
									const top = rect.bottom - containerRect.top + 2;
									const left = rect.left - containerRect.left;
									setPopupPos({ top, left });
									return;
								}
							}
						}
					}
				}
				setActive(false);
				setSuggestions([]);
			});
		});
	}, [editor]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLDivElement>): boolean => {
			if (!active || !suggestions.length) return false;
			if (e.key === 'ArrowDown') {
				setSelectedIndex((i) => (i + 1) % suggestions.length);
				e.preventDefault();
				return true;
			} else if (e.key === 'ArrowUp') {
				setSelectedIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
				e.preventDefault();
				return true;
			} else if (e.key === 'Tab') {
				e.preventDefault();
				e.stopPropagation();
				const selected = suggestions[selectedIndex];
				if (selected) handleSelect(selected);
				return true;
			} else if (e.key === 'Escape') {
				setActive(false);
				return true;
			} else if (e.key === 'Enter') {
				e.preventDefault();
				e.stopPropagation();
				const selected = suggestions[selectedIndex];
				if (selected) handleSelect(selected);
				return true;
			}
			return false;
		},
		[active, suggestions, selectedIndex, handleSelect]
	);

	const popupVisible = active && suggestions.length > 0;

	return (
		<EmojiSuggestionContext.Provider
			value={{ active, suggestions, selectedIndex, handleKeyDown, popupVisible, justInsertedEmoji }}
		>
			{children}
			{popupVisible && (
				<EmojiSuggestionPopup
					suggestions={suggestions}
					selectedIndex={selectedIndex}
					onSelect={handleSelect}
					onHover={setSelectedIndex}
					position={popupPos}
				/>
			)}
		</EmojiSuggestionContext.Provider>
	);
};
