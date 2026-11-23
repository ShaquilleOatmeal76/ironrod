// Tiptap extensions for Iron Rod notes:
//   @Alma 32:21  -> a verseRef chip (stores the verse id range)
//   #faith       -> a tag chip
// Both are "mention" nodes: atomic inline chips the cursor treats as one unit.

import StarterKit from '@tiptap/starter-kit';
import Mention from '@tiptap/extension-mention';
import { Placeholder } from '@tiptap/extensions';
import { PluginKey } from '@tiptap/pm/state';
import { api } from '#lib/api.js';
import { renderer } from './suggest.svelte.js';

export const VerseRef = Mention.extend({
	name: 'verseRef',
	addAttributes() {
		return {
			...this.parent?.(),
			start: {
				default: null,
				parseHTML: (el) => Number(el.getAttribute('data-start')) || null
			},
			end: {
				default: null,
				parseHTML: (el) => Number(el.getAttribute('data-end')) || null
			}
		};
	}
}).configure({
	renderText: ({ node }) => node.attrs.label,
	renderHTML: ({ node }) => [
		'span',
		{
			'data-type': 'verseRef',
			'data-id': node.attrs.label,
			'data-label': node.attrs.label,
			'data-start': node.attrs.start,
			'data-end': node.attrs.end
		},
		node.attrs.label
	],
	suggestion: {
		char: '@',
		pluginKey: new PluginKey('verseRef'),
		allowSpaces: true,
		items: async ({ query }) => {
			if (!query.trim()) return [{ type: 'hint' }];
			try {
				const res = await api.suggestRefs(query);
				if (res.refs.length) return res.refs.map((r) => ({ type: 'ref', ...r }));
				return res.books.map((b) => ({ type: 'book', ...b }));
			} catch {
				return [];
			}
		},
		command: ({ editor, range, props: p }) => {
			const props = /** @type {any} */ (p);
			if (props.type === 'hint') return;
			if (props.type === 'book') {
				// finish the book name and keep typing the chapter:verse
				editor.chain().focus().insertContentAt(range, `@${props.title} `).run();
				return;
			}
			editor
				.chain()
				.focus()
				.insertContentAt(range, [
					{
						type: 'verseRef',
						attrs: { id: props.label, label: props.label, start: props.start_verse_id, end: props.end_verse_id }
					},
					{ type: 'text', text: ' ' }
				])
				.run();
		},
		render: renderer('ref')
	}
});

export const Tag = Mention.extend({ name: 'tag' }).configure({
	renderText: ({ node }) => `#${node.attrs.id}`,
	renderHTML: ({ node }) => [
		'span',
		{ 'data-type': 'tag', 'data-id': node.attrs.id, 'data-label': node.attrs.id },
		`#${node.attrs.id}`
	],
	suggestion: {
		char: '#',
		pluginKey: new PluginKey('tag'),
		items: async ({ query }) => {
			const q = query.trim().toLowerCase().replace(/[^\p{L}\p{N}_-]/gu, '');
			let existing = [];
			try {
				existing = (await api.tags(q)).map((t) => ({ type: 'tag', name: t.name, count: t.count }));
			} catch {
				/* offline: still allow new tags */
			}
			if (q && !existing.some((t) => t.name === q)) existing.push({ type: 'new', name: q });
			return existing.slice(0, 8);
		},
		command: ({ editor, range, props: p }) => {
			const props = /** @type {any} */ (p);
			editor
				.chain()
				.focus()
				.insertContentAt(range, [
					{ type: 'tag', attrs: { id: props.name, label: props.name } },
					{ type: 'text', text: ' ' }
				])
				.run();
		},
		render: renderer('tag')
	}
});

export function noteExtensions(placeholder) {
	return [
		StarterKit.configure({
			heading: { levels: [2, 3] },
			link: false,
			underline: false,
			codeBlock: false,
			horizontalRule: false
		}),
		Placeholder.configure({ placeholder }),
		VerseRef,
		Tag
	];
}
