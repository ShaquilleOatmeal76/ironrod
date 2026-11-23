// Small wrapper around the Iron Rod API.

/** @param {typeof fetch} f @param {string} path */
async function get(f, path) {
	const res = await f(`/api${path}`);
	if (!res.ok) {
		const err = new Error(`${res.status} ${res.statusText}`);
		// @ts-ignore
		err.status = res.status;
		throw err;
	}
	return res.json();
}

export const api = {
	/** @param {typeof fetch} f */
	volumes: (f = fetch) => get(f, '/volumes'),
	/** @param {string} volume @param {string} book @param {number|string} chapter @param {typeof fetch} f */
	chapter: (volume, book, chapter, f = fetch) => get(f, `/read/${volume}/${book}/${chapter}`),
	/** @param {typeof fetch} f */
	health: (f = fetch) => get(f, '/health')
};

/** Build the app URL for a chapter (and optional verse). */
export function chapterHref(volume, book, chapter, verse = null) {
	return `/read/${volume}/${book}/${chapter}${verse ? `#v${verse}` : ''}`;
}
