import data from '@emoji-mart/data';

// EmojiMartEmoji type matches the structure of emoji-mart's emoji objects
export type EmojiMartEmoji = {
	id: string;
	shortcodes?: string[];
	skins?: { native: string }[];
};

// EmojiMartData type for the imported data
export type EmojiMartData = {
	emojis: Record<string, EmojiMartEmoji>;
};

export function findEmojiByShortcode(shortcode: string): string | undefined {
	const emojis = (data as EmojiMartData).emojis;
	if (!emojis) return undefined;
	// Try direct lookup
	const emojiObj = emojis[shortcode];
	if (emojiObj) return emojiObj.skins?.[0]?.native;
	// Try alternate shortcodes
	for (const key in emojis) {
		const emoji = emojis[key];
		if (emoji && emoji.shortcodes && emoji.shortcodes.includes(shortcode)) {
			return emoji.skins?.[0]?.native;
		}
	}
	return undefined;
}

export function searchEmojisByShortcode(query: string, maxResults = 10): EmojiMartEmoji[] {
	const emojis = (data as EmojiMartData).emojis;
	if (!emojis || !query) return [];
	const lower = query.toLowerCase();
	const results: EmojiMartEmoji[] = [];
	for (const key in emojis) {
		const emoji = emojis[key];
		if (
			emoji &&
			((emoji.id && emoji.id.includes(lower)) ||
				(emoji.shortcodes && emoji.shortcodes.some((sc) => sc.includes(lower))))
		) {
			results.push(emoji);
			if (results.length >= maxResults) break;
		}
	}
	return results;
}
