<script>
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '#lib/api.js';

	/** @type {{ params?: Record<string, any>, height?: string, compact?: boolean }} */
	let { params = {}, height = '100%', compact = false } = $props();

	let el = $state();
	let cy = null;
	let info = $state(/** @type {any} */ (null));
	let counts = $state({ nodes: 0, edges: 0 });
	let loading = $state(true);
	let failed = $state(false);

	const COLORS = { verse: '#7DA2FF', talk: '#C89BFF', note: '#F5B454' };

	async function load() {
		loading = true;
		failed = false;
		try {
			const [{ default: cytoscape }, data] = await Promise.all([import('cytoscape'), api.graph(params)]);
			counts = { nodes: data.nodes.length, edges: data.edges.length };
			const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#5EEAD4';
			const centerId = params.verse_id != null ? `v:${params.verse_id}-${params.verse_id}` : params.para_id != null ? `p:${params.para_id}` : null;
			cy?.destroy();
			cy = cytoscape({
				container: el,
				elements: [
					...data.nodes.map((n) => ({ data: { ...n, color: COLORS[n.kind], center: n.id === centerId ? 1 : 0 } })),
					...data.edges.map((e, i) => ({ data: { id: `e${i}`, ...e } }))
				],
				style: [
					{
						selector: 'node',
						style: {
							'background-color': '#12161B',
							'border-width': 2,
							'border-color': 'data(color)',
							label: 'data(label)',
							color: '#B4BECC',
							'font-family': 'JetBrains Mono Variable, monospace',
							'font-size': compact ? 9 : 11,
							'text-valign': 'bottom',
							'text-margin-y': 6,
							'text-wrap': 'ellipsis',
							'text-max-width': compact ? '90px' : '160px',
							width: compact ? 20 : 26,
							height: compact ? 20 : 26
						}
					},
					{ selector: 'node[kind = "talk"]', style: { shape: 'round-rectangle' } },
					{ selector: 'node[kind = "note"]', style: { shape: 'round-tag' } },
					{ selector: 'node[center = 1]', style: { 'border-color': accent, 'background-color': '#0F2A28', width: 36, height: 36, color: '#E6EAF0' } },
					{
						selector: 'edge',
						style: { width: 1.5, 'line-color': '#2A3340', 'curve-style': 'bezier', label: compact ? '' : 'data(label)', 'font-size': 9, color: '#5d6878', 'text-rotation': 'autorotate', 'font-family': 'JetBrains Mono Variable, monospace' }
					},
					{ selector: 'node:selected', style: { 'border-color': '#E6EAF0', 'border-width': 3 } }
				],
				layout: { name: data.nodes.length > 1 ? 'cose' : 'grid', animate: false, padding: 24, nodeRepulsion: () => 9000, idealEdgeLength: () => (compact ? 70 : 110) },
				minZoom: 0.2,
				maxZoom: compact ? 1.3 : 1.6,
				wheelSensitivity: 0.25
			});
			cy.on('tap', 'node', (e) => (info = e.target.data()));
			cy.on('tap', (e) => e.target === cy && (info = null));
			cy.on('dbltap', 'node', (e) => goto(e.target.data('href')));
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	onMount(load);
	onDestroy(() => cy?.destroy());
</script>

<div class="wrap" style="height:{height}">
	<div class="canvas" bind:this={el} role="img" aria-label="Graph of {counts.nodes} connected verses, talks and notes"></div>
	{#if loading}<p class="state mono">loading graph…</p>{/if}
	{#if failed}<p class="state mono">couldn't load the graph</p>{/if}
	{#if !loading && !failed && counts.nodes <= 1}
		<p class="state">Nothing connected yet. Links, notes and @references show up here.</p>
	{/if}
	<div class="legend mono" aria-hidden="true">
		<span><i style="--c:#7DA2FF"></i>verse</span><span><i class="sq" style="--c:#C89BFF"></i>talk</span><span><i style="--c:#F5B454"></i>note</span>
		{#if !compact}<span class="faint">{counts.nodes} nodes · {counts.edges} links · double-click to open</span>{/if}
	</div>
	{#if info}
		<div class="info">
			<div class="mono k" style="color:{COLORS[info.kind]}">{info.kind.toUpperCase()}</div>
			<div class="t">{info.label}</div>
			<p>{info.text}</p>
			<a class="mono" href={info.href}>open →</a>
		</div>
	{/if}
</div>

<style>
	.wrap { position: relative; min-height: 220px; }
	.canvas { position: absolute; inset: 0; }
	.state { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; margin: 0; padding: 20px; text-align: center; color: var(--text-faint); font-size: 13px; pointer-events: none; }
	.legend { position: absolute; left: 10px; bottom: 8px; display: flex; flex-wrap: wrap; gap: 12px; font-size: 11px; color: var(--text-muted); pointer-events: none; }
	.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; border: 2px solid var(--c); margin-right: 5px; vertical-align: -1px; }
	.legend i.sq { border-radius: 2px; }
	.faint { color: var(--text-faint); }
	.info {
		position: absolute; right: 10px; top: 10px; width: min(300px, calc(100% - 20px));
		background: var(--bg-raised); border: 1px solid var(--border-strong); border-radius: 8px; padding: 12px 14px;
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
	}
	.k { font-size: 10px; letter-spacing: 0.12em; }
	.t { font-weight: 600; font-size: 14px; margin: 4px 0; }
	.info p { margin: 0 0 8px; font-size: 13px; line-height: 1.5; color: var(--text-muted); max-height: 110px; overflow: hidden; }
	.info a { font-size: 12px; }
</style>
