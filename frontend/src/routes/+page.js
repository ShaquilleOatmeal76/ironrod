import { redirect } from '@sveltejs/kit';
import { lastRead } from '#lib/reader.svelte.js';
import { chapterHref } from '#lib/api.js';

// The home page just reopens wherever you left off.
export function load() {
	const { volume, book, chapter } = lastRead();
	redirect(307, chapterHref(volume, book, chapter));
}
