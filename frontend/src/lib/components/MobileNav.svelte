<script>
	import { page } from '$app/state';
	import { chapterHref } from '#lib/api.js';
	import { lastRead } from '#lib/reader.svelte.js';
	import { openPalette } from '#lib/commands.svelte.js';

	// Bottom tab bar on phones (replaces the status bar there).
	const readHref = $derived.by(() => {
		page.url.pathname; // recompute after navigating
		const l = lastRead();
		return chapterHref(l.volume, l.book, l.chapter);
	});
	const at = (p) => page.url.pathname.startsWith(p);
</script>

<nav class="tabs" aria-label="Main">
	<a href={readHref} aria-current={at('/read') ? 'page' : undefined}>
		<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 6c-2-1.5-5-2-8-1.5v13c3-.5 6 0 8 1.5 2-1.5 5-2 8-1.5v-13c-3-.5-6 0-8 1.5zM12 6v13" /></svg>Read
	</a>
	<a href="/library" aria-current={at('/library') || at('/doc') ? 'page' : undefined}>
		<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h5v14H4zM10 5h4v14h-4zM15.5 5.5l3.8-1 3 13.5-3.8 1z" /></svg>Talks
	</a>
	<a href="/plans" aria-current={at('/plans') ? 'page' : undefined}>
		<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></svg>Plans
	</a>
	<a href="/notes" aria-current={at('/notes') ? 'page' : undefined}>
		<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6z" /><path d="M9 12h7M9 16h5" /></svg>Notes
	</a>
	<button onclick={() => openPalette()}>
		<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>Search
	</button>
</nav>

<style>
	.tabs { display: none; }
	@media (max-width: 900px) {
		.tabs {
			display: grid;
			grid-template-columns: repeat(5, minmax(0, 1fr));
			flex: 0 0 auto;
			padding: 6px 6px calc(6px + env(safe-area-inset-bottom));
			border-top: 1px solid var(--border);
			background: var(--bg-raised);
		}
	}
	a, button {
		all: unset;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		min-height: 48px;
		justify-content: center;
		border-radius: 8px;
		font-size: 11px;
		color: var(--text-faint);
		cursor: pointer;
	}
	a:focus-visible, button:focus-visible { outline: 2px solid var(--accent); }
	[aria-current='page'] { color: var(--accent); font-weight: 600; }
	svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
</style>
