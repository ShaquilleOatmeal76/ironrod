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
	deleteLink: (id) => request(fetch, `/links/${id}`, { method: 'DELETE' }),

	// talks, speeches, lessons
	library: (f = fetch) => get(f, '/library'),
	collection: (id, f = fetch) => get(f, `/collections/${id}`),
	doc: (id, f = fetch) => get(f, `/docs/${id}`),
	deleteDoc: (id) => request(fetch, `/docs/${id}`, { method: 'DELETE' }),
	para: (id) => get(fetch, `/paras/${id}`),
	setParaHighlight: (para_id, color) => request(fetch, '/para-highlights', { method: 'PUT', body: { para_id, color } }),
	createParaNote: (body_html, para_id) => request(fetch, '/notes', { method: 'POST', body: { body_html, para_id } }),
	createParaLink: (para_id, { to = null, start = null, end = null, label = 'related' }) =>
		request(fetch, '/para-links', { method: 'POST', body: { para_id, to, start_verse_id: start, end_verse_id: end, label } }),
	deleteParaLink: (id) => request(fetch, `/para-links/${id}`, { method: 'DELETE' }),
	cfmWeek: (on) => get(fetch, `/cfm/week?${qs({ on })}`),
	startImport: (body) => request(fetch, '/import', { method: 'POST', body }),
	importJobs: () => get(fetch, '/import/jobs'),

	// plans & tracking
	markRead: (volume, book, chapter, read = true) =>
		request(fetch, '/read-log', { method: 'POST', body: { volume, book, chapter, read, today: today() } }),
	chapterStatus: (volume, book, chapter, f = fetch) => get(f, `/read-log/${volume}/${book}/${chapter}?today=${today()}`),
	plans: () => get(fetch, `/plans?today=${today()}`),
	previewPlan: (body) => request(fetch, '/plans/preview', { method: 'POST', body }),
	createPlan: (body) => request(fetch, '/plans', { method: 'POST', body }),
	archivePlan: (id) => request(fetch, `/plans/${id}`, { method: 'DELETE' }),
	stats: () => get(fetch, `/stats?today=${today()}`),
	setGoal: (kind, target) => request(fetch, '/goals', { method: 'PUT', body: { kind, target } }),

	// graph
	graph: (params = {}) => get(fetch, `/graph?${qs(params)}`)
};

/** Today's date in the reader's own time zone, as YYYY-MM-DD. */
export function today(d = new Date()) {
	const pad = (n) => String(n).padStart(2, '0');
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** URL for a talk paragraph. */
export function paraHref(p) {
	return `/doc/${p.doc_id}#p${p.position}`;
}

/** Build the app URL for a chapter (and optional verse). */
export function chapterHref(volume, book, chapter, verse = null) {
	return `/read/${volume}/${book}/${chapter}${verse ? `#v${verse}` : ''}`;
}

/** URL for a described range ({volume, book, chapter, verse}). */
export function refHref(r) {
	return chapterHref(r.volume, r.book, r.chapter, r.verse);
}
