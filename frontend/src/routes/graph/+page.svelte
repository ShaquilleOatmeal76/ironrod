<script>
	import { reader } from '#lib/reader.svelte.js';
	import GraphView from '#lib/components/GraphView.svelte';
	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});
</script>

<svelte:head><title>Graph · Iron Rod</title></svelte:head>

<div class="wrap">
	<header>
		<h1>Study graph</h1>
		<p>Every verse, talk paragraph and note you've connected. Tap a node for a preview, double-click to open it.</p>
	</header>
	<div class="frame"><GraphView height="100%" /></div>
</div>

<style>
	.wrap { height: 100%; display: flex; flex-direction: column; padding: 24px; gap: 14px; box-sizing: border-box; }
	h1 { margin: 0; font-family: var(--font-scripture); font-weight: 600; font-size: 32px; }
	p { margin: 4px 0 0; color: var(--text-muted); font-size: 14px; }
	.frame { flex: 1; min-height: 360px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg-raised); overflow: hidden;
		background-image: radial-gradient(circle, #1a2029 1px, transparent 1px); background-size: 22px 22px; }
</style>
