<script>
	import { reader } from '#lib/reader.svelte.js';

	const ref = $derived(
		reader.current
			? `${reader.current.book_title} ${reader.current.chapter}${reader.verse ? ':' + reader.verse : ''}`
			: '—'
	);
</script>

<footer class="status mono" aria-label="Status bar">
	<span class="mode">READ</span>
	<span class="seg ref">{ref}</span>
	<span class="grow"></span>
	<span class="seg keys">j/k verse · [ ] chapter · esc clear</span>
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
</style>
