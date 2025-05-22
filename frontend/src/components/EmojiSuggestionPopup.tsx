import React from 'react';
import type { EmojiMartEmoji } from '../utils/emojiUtils';

type Props = {
	suggestions: EmojiMartEmoji[];
	selectedIndex: number;
	onSelect: (emoji: EmojiMartEmoji) => void;
	onHover: (index: number) => void;
	position: { top: number; left: number };
};

export const EmojiSuggestionPopup: React.FC<Props> = ({
	suggestions,
	selectedIndex,
	onSelect,
	onHover,
	position,
}) => {
	if (!suggestions.length) return null;
	return (
		<ul
			style={{
				position: 'absolute',
				top: position.top,
				left: position.left,
				background: '#fffbe6',
				border: '2px solid #fbbf24',
				borderRadius: 4,
				boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
				zIndex: 9999,
				listStyle: 'none',
				margin: 0,
				padding: 0,
				minWidth: 180,
			}}
		>
			{suggestions.map((emoji, i) => (
				<li
					key={emoji.id}
					onMouseDown={(e) => {
						e.preventDefault();
						onSelect(emoji);
					}}
					onMouseEnter={() => onHover(i)}
					style={{
						padding: '6px 12px',
						background: i === selectedIndex ? '#f0f0f0' : 'white',
						cursor: 'pointer',
						display: 'flex',
						alignItems: 'center',
					}}
				>
					<span style={{ fontSize: 20, marginRight: 8 }}>{emoji.skins?.[0]?.native}</span>
					<span>:{emoji.id}:</span>
				</li>
			))}
		</ul>
	);
};
