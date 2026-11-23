import { api } from '#lib/api.js';

// Single-page app: everything renders in the browser.
export const ssr = false;
export const prerender = false;

export async function load({ fetch }) {
	return { volumes: await api.volumes(fetch) };
}
