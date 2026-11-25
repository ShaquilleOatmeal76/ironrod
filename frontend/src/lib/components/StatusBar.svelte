<script>
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { reader, progress, refreshProgress } from '#lib/reader.svelte.js';

	onMount(refreshProgress);
	const plan = $derived(progress.plans.find((p) => p.kind === 'range') ?? progress.plans[0]);
	const mode = $derived(
		page.url.pathname.startsWith('/plans') ? 'PLANS'
		: page.url.pathname.startsWith('/doc') || page.url.pathname.startsWith('/library') ? 'TALKS'
		: page.url.pathname.startsWith('/notes') ? 'NOTES'
		: page.url.pathname.startsWith('/split') ? 'SPLIT'
		: page.url.pathname.startsWith('/graph') ? 'GRAPH'
		: page.url.pathname.startsWith('/search') ? 'SEARCH' : 'READ'
	);

	const ref = $derived(
		reader.current
			? `${reader.current.book_title} ${reader.current.chapter}${reader.verse ? ':' + reader.verse : ''}`
			: '—'
	);
</script>

<footer class="status mono" aria-label="Status bar">
	<span class="mode">{mode}</span>
	<span class="seg ref">{ref}</span>
	{#if plan}
		<a class="seg link" href="/plans">{plan.title.toLowerCase().slice(0, 28)} <span class:warn={plan.behind} class="pct">{plan.total ? Math.round((100 * plan.done) / plan.total) : 0}%</span></a>
	{/if}
	{#if progress.loaded}
		<span class="seg">today {progress.todayChapters} ch</span>
		{#if progress.streak}<span class="seg">streak {progress.streak}d</span>{/if}
	{/if}
	<span class="grow"></span>
	<span class="seg keys">⌘K palette · j/k verse · 1–4 highlight · n note · ? keys</span>
	<span class="seg sync" class:offline={!reader.online}>
		● {reader.online ? 'connected' : 'offline'}
	</span>
</footer>

<style>
	.status {
		display: flex;
		align-items: stretch;
		border-top: 1px solid var(--border);
		background: var(--bg-raised);
		font-size: 12px;
		color: var(--text-faint);
		min-height: 30px;
	}
	.mode {
		display: flex;
		align-items: center;
		padding: 0 12px;
		background: var(--accent);
		color: var(--accent-ink);
		font-weight: 600;
	}
	.seg { display: flex; align-items: center; padding: 0 12px; }
	.ref { color: var(--text); border-right: 1px solid var(--border); }
	.grow { flex: 1; }
	.sync { border-left: 1px solid var(--border); color: var(--accent); }
	.sync.offline { color: var(--hl-promise); }
	@media (max-width: 700px) {
		.keys { display: none; }
	}
	.seg + .seg { border-left: 1px solid var(--border); }
	.link { color: inherit; text-decoration: none; }
	.link:hover { color: var(--text); }
	.pct { color: var(--accent); margin-left: 6px; }
	.pct.warn { color: var(--hl-promise); }
	@media (max-width: 900px) {
		.status { display: none; }
	}
</style>
