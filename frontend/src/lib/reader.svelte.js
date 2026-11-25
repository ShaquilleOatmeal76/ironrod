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

// Reading progress shown in the status bar and plans page. Call
// refreshProgress() after marking something read or writing a note.
import { api } from './api.js';

export const progress = $state({
	streak: 0,
	todayChapters: 0,
	/** @type {any[]} */
	plans: [],
	loaded: false
});

export async function refreshProgress() {
	try {
		const [s, p] = await Promise.all([api.stats(), api.plans()]);
		progress.streak = s.streak;
		progress.todayChapters = s.today_chapters;
		progress.plans = p;
		progress.loaded = true;
	} catch {
		/* offline: keep what we had */
	}
}

// "Install app": browsers that support it hand us a prompt we can show later.
export const install = $state({
	/** @type {any} */
	prompt: null,
	installed: false,
	ios: false
});

export function watchInstall() {
	install.installed = window.matchMedia('(display-mode: standalone)').matches || /** @type {any} */ (navigator).standalone === true;
	install.ios = /iphone|ipad|ipod/i.test(navigator.userAgent) && !install.installed;
	window.addEventListener('beforeinstallprompt', (e) => {
		e.preventDefault();
		install.prompt = e;
	});
	window.addEventListener('appinstalled', () => {
		install.prompt = null;
		install.installed = true;
	});
}

export async function promptInstall() {
	if (!install.prompt) return false;
	install.prompt.prompt();
	await install.prompt.userChoice;
	install.prompt = null;
	return true;
}
