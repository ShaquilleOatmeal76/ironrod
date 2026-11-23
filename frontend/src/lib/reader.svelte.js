// Shared reading state, so the header, sidebar and status bar can all see
// what's open without passing props everywhere. (Svelte 5 runes.)

export const reader = $state({
	/** @type {{volume:string, book:string, book_title:string, chapter:number} | null} */
	current: null,
	/** currently selected verse number, or null */
	verse: /** @type {number|null} */ (null),
	sidebarOpen: false,
	online: true
});

const LAST_KEY = 'ironrod:last';

export function rememberLast(volume, book, chapter) {
	try {
		localStorage.setItem(LAST_KEY, JSON.stringify({ volume, book, chapter }));
	} catch {
		/* storage unavailable: fine */
	}
}

export function lastRead() {
	try {
		const raw = localStorage.getItem(LAST_KEY);
		if (raw) return JSON.parse(raw);
	} catch {
		/* ignore */
	}
	return { volume: 'bofm', book: '1-ne', chapter: 1 };
}
