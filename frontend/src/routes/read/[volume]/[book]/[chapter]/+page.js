import { error } from '@sveltejs/kit';
import { api } from '#lib/api.js';

export async function load({ params, fetch }) {
	try {
		const [chapter, annotations] = await Promise.all([
			api.chapter(params.volume, params.book, params.chapter, fetch),
			api.annotations(params.volume, params.book, params.chapter, fetch)
		]);
		return { chapter, annotations };
	} catch (e) {
		error(e.status === 404 ? 404 : 500, e.status === 404 ? 'Chapter not found' : 'Could not load chapter');
	}
}
