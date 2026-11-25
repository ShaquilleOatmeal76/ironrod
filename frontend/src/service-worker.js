/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />
// Iron Rod service worker: makes the app installable and keeps working
// offline for anything you've already opened.
//
// - App files (JS/CSS/fonts/icons) are cached when a new version installs.
// - Pages always load the app shell, from the network or (offline) the cache.
// - Scripture, talks and the library use "stale while revalidate": instant
//   from cache, refreshed in the background, so chapters you've read open offline.
// - Other API reads try the network first and fall back to the last copy.
// - Saving (POST/PUT/PATCH/DELETE) always goes to the server.
import { immutable, assets } from '$app/manifest';

const abs = (p) => (p.startsWith('/') ? p : `/${p}`);
const build = immutable.map((f) => abs(f.path));
const files = assets.map((f) => abs(f.path));
// A fingerprint of this build's file names (they contain content hashes),
// so each new build gets a fresh cache and old ones are cleaned up.
const version = build.reduce((h, p) => (Math.imul(31, h) + [...p].reduce((a, c) => (a * 33 + c.charCodeAt(0)) | 0, 0)) | 0, 7).toString(36);

const sw = /** @type {ServiceWorkerGlobalScope} */ (/** @type {unknown} */ (self));
const APP = `app-${version}`;
const DATA = 'data-v1';
const SHELL = '/index.html';
const STALE_OK = [/^\/api\/read\//, /^\/api\/volumes$/, /^\/api\/docs\/\d+$/, /^\/api\/library$/, /^\/api\/collections\/\d+$/];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		(async () => {
			const cache = await caches.open(APP);
			await cache.addAll([...build, ...files]);
			// the SPA shell: FastAPI serves index.html for any page URL
			const shell = await fetch('/', { cache: 'reload' });
			if (shell.ok) await cache.put(SHELL, shell);
			await sw.skipWaiting();
		})()
	);
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			for (const key of await caches.keys()) if (key !== APP && key !== DATA) await caches.delete(key);
			await sw.clients.claim();
		})()
	);
});

sw.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	const url = new URL(req.url);
	if (url.origin !== sw.location.origin) return;

	// app pages -> network, falling back to the cached shell
	if (req.mode === 'navigate') {
		event.respondWith(
			(async () => {
				try {
					const res = await fetch(req);
					if (res.ok) (await caches.open(APP)).put(SHELL, res.clone());
					return res;
				} catch {
					return (await caches.match(SHELL)) ?? Response.error();
				}
			})()
		);
		return;
	}

	// built assets and static files -> cache first (they're versioned)
	if (build.includes(url.pathname) || files.includes(url.pathname)) {
		event.respondWith(caches.match(req).then((hit) => hit ?? fetch(req)));
		return;
	}

	if (!url.pathname.startsWith('/api/') || url.pathname === '/api/health') return;

	if (STALE_OK.some((re) => re.test(url.pathname))) {
		event.respondWith(
			(async () => {
				const cache = await caches.open(DATA);
				const hit = await cache.match(req);
				const fresh = fetch(req)
					.then((res) => {
						if (res.ok) cache.put(req, res.clone());
						return res;
					})
					.catch(() => hit ?? Response.error());
				if (hit) {
					event.waitUntil(fresh.then(() => undefined));
					return hit;
				}
				return fresh;
			})()
		);
		return;
	}

	event.respondWith(
		(async () => {
			const cache = await caches.open(DATA);
			try {
				const res = await fetch(req);
				if (res.ok) cache.put(req, res.clone());
				return res;
			} catch {
				return (await cache.match(req)) ?? new Response(JSON.stringify({ detail: 'offline' }), { status: 503, headers: { 'content-type': 'application/json' } });
			}
		})()
	);
});
