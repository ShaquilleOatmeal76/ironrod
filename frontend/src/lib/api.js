// Small wrapper around the Iron Rod API.

/**
 * @param {typeof fetch} f
 * @param {string} path
 * @param {{ method?: string, body?: any }} [opts]
 */
async function request(f, path, { method = 'GET', body = undefined } = {}) {
	const res = await f(`/api${path}`, {
		method,
		headers: body !== undefined ? { 'content-type': 'application/json' } : undefined,
		body: body !== undefined ? JSON.stringify(body) : undefined
	});
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const j = await res.json();
			detail = typeof j.detail === 'string' ? j.detail : detail;
		} catch {
			/* not JSON */
		}
		const err = new Error(detail);
		// @ts-ignore
		err.status = res.status;
		throw err;
	}
	return res.status === 204 ? null : res.json();
}

const get = (f, path) => request(f, path);
const qs = (params) => new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString();

export const api = {
	// library
	volumes: (f = fetch) => get(f, '/volumes'),
	chapter: (volume, book, chapter, f = fetch) => get(f, `/read/${volume}/${book}/${chapter}`),
	health: (f = fetch) => get(f, '/health'),

	// search (command palette + search page)
	search: (q, params = {}) => get(fetch, `/search?${qs({ q, ...params })}`),

	// references
	resolveRef: (q) => get(fetch, `/refs/resolve?${qs({ q })}`),
	suggestRefs: (q) => get(fetch, `/refs/suggest?${qs({ q })}`),

	// markup
	annotations: (volume, book, chapter, f = fetch) => get(f, `/annotations/${volume}/${book}/${chapter}`),
	verse: (id) => get(fetch, `/verses/${id}`),
	setHighlight: (start, end, color) =>
		request(fetch, '/highlights', { method: 'PUT', body: { start_verse_id: start, end_verse_id: end, color } }),

	notes: (params = {}) => get(fetch, `/notes?${qs(params)}`),
	createNote: (body_html, start = null, end = null) =>
		request(fetch, '/notes', { method: 'POST', body: { body_html, start_verse_id: start, end_verse_id: end } }),
	updateNote: (id, body_html) => request(fetch, `/notes/${id}`, { method: 'PATCH', body: { body_html } }),
	deleteNote: (id) => request(fetch, `/notes/${id}`, { method: 'DELETE' }),
	tags: (q = '') => get(fetch, `/tags?${qs({ q })}`),

	linkLabels: () => get(fetch, '/links/labels'),
	createLink: (start, end, to, label) =>
		request(fetch, '/links', {
			method: 'POST',
			body: { from_start_verse_id: start, from_end_verse_id: end, to, label }
		}),
	deleteLink: (id) => request(fetch, `/links/${id}`, { method: 'DELETE' })
};

/** Build the app URL for a chapter (and optional verse). */
export function chapterHref(volume, book, chapter, verse = null) {
	return `/read/${volume}/${book}/${chapter}${verse ? `#v${verse}` : ''}`;
}

/** URL for a described range ({volume, book, chapter, verse}). */
export function refHref(r) {
	return chapterHref(r.volume, r.book, r.chapter, r.verse);
}
