import { DecoratorNode, LexicalNode, NodeKey, SerializedLexicalNode, Spread } from 'lexical';
import type { JSX } from 'react';
import { findEmojiByShortcode } from '../utils/emojiUtils';

export type SerializedEmojiNode = Spread<
	{
		shortcode: string;
		type: 'emoji';
		version: 1;
	},
	SerializedLexicalNode
>;

export class EmojiNode extends DecoratorNode<JSX.Element> {
	__shortcode: string;

	static getType(): string {
		return 'emoji';
	}

	static clone(node: EmojiNode): EmojiNode {
		return new EmojiNode(node.__shortcode, node.__key);
	}

	constructor(shortcode: string, key?: NodeKey) {
		super(key);
		this.__shortcode = shortcode;
	}

	createDOM(): HTMLElement {
		const span = document.createElement('span');
		span.className = 'emoji-node';
		return span;
	}

	updateDOM(): boolean {
		return false;
	}

	decorate(): JSX.Element {
		const emoji = findEmojiByShortcode(this.__shortcode);
		return (
			<span
				className='emoji-node'
				style={{ fontSize: '1.2em', verticalAlign: 'middle' }}
				title={`:${this.__shortcode}:`}
			>
				{emoji || `:${this.__shortcode}:`}
			</span>
		);
	}

	exportJSON(): SerializedEmojiNode {
		return {
			type: 'emoji',
			version: 1,
			shortcode: this.__shortcode,
		};
	}

	static importJSON(serializedNode: SerializedEmojiNode): EmojiNode {
		return new EmojiNode(serializedNode.shortcode);
	}
}

export function $createEmojiNode(shortcode: string): EmojiNode {
	return new EmojiNode(shortcode);
}

export function $isEmojiNode(node: LexicalNode | null | undefined): node is EmojiNode {
	return node instanceof EmojiNode;
}
