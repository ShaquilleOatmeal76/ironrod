import { error } from '@sveltejs/kit';
import { api } from '#lib/api.js';

export async function load({ params, fetch }) {
	try {
		return { doc: await api.doc(params.id, fetch) };
	} catch (e) {
		error(e.status === 404 ? 404 : 500, e.status === 404 ? 'Not found' : 'Could not load');
	}
}
