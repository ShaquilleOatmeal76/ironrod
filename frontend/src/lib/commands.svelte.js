import { untrack } from 'svelte';

// The command palette's state and its list of commands.
//
// Global commands are registered once by the layout. Pages add their own
// while they're open (the reader adds "highlight", "note", "copy"...) by
// calling registerCommands() inside an $effect and returning its cleanup.

/**
 * @typedef {{
 *   id: string, title: string, group?: string, keys?: string, hint?: string,
 *   run: () => void, when?: () => boolean
 * }} Command
 */

export const palette = $state({
	open: false,
	query: '',
	help: false,
	/** when "g" was last pressed (two-key shortcuts like g n) */
	gAt: 0
});

export function openPalette(query = '') {
	palette.query = query;
	palette.open = true;
}

export function closePalette() {
	palette.open = false;
}

/** @type {Command[][]} */
const sources = $state([]);

/** @param {Command[]} list @returns {() => void} */
export function registerCommands(list) {
	// untrack: callers run this inside an $effect. Without it, the effect would
	// "depend" on the very list it changes and re-run forever.
	untrack(() => sources.push(list));
	return () =>
		untrack(() => {
			const i = sources.indexOf(list);
			if (i >= 0) sources.splice(i, 1);
		});
}

const GROUP_ORDER = ['verse', 'notes', 'go', 'help'];

/** All commands available right now, most specific (verse) first. */
export function availableCommands() {
	const seen = new Set();
	const out = [];
	for (const list of sources) {
		for (const c of list) {
			if (seen.has(c.id) || (c.when && !c.when())) continue;
			seen.add(c.id);
			out.push(c);
		}
	}
	const rank = (c) => {
		const i = GROUP_ORDER.indexOf(c.group ?? '');
		return i < 0 ? GROUP_ORDER.length : i;
	};
	return out.sort((a, b) => rank(a) - rank(b));
}

/** Loose match: every typed word appears somewhere in the title/hint. */
export function matchCommand(c, query) {
	const words = query.toLowerCase().split(/\s+/).filter(Boolean);
	const hay = `${c.title} ${c.hint ?? ''} ${c.group ?? ''}`.toLowerCase();
	return words.every((w) => hay.includes(w));
}

// --- recently visited chapters (shown when the palette opens empty) ---
const RECENT_KEY = 'ironrod:recent';

export function recentChapters() {
	try {
		return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
	} catch {
		return [];
	}
}

export function pushRecent(entry) {
	try {
		const list = recentChapters().filter((r) => r.href !== entry.href);
		list.unshift(entry);
		localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, 6)));
	} catch {
		/* storage unavailable */
	}
}
