<script>
	import '@fontsource-variable/inter';
	import '@fontsource-variable/jetbrains-mono';
	import '@fontsource-variable/source-serif-4';
	import '../app.css';

	import { onMount } from 'svelte';
	import Sidebar from '#lib/components/Sidebar.svelte';
	import StatusBar from '#lib/components/StatusBar.svelte';
	import { reader } from '#lib/reader.svelte.js';
	import { api } from '#lib/api.js';

	let { data, children } = $props();

	// Ping the server now and then so the status bar can show "offline".
	onMount(() => {
		const check = () =>
			api.health().then(
				() => (reader.online = true),
				() => (reader.online = false)
			);
		const id = setInterval(check, 30000);
		return () => clearInterval(id);
	});
</script>

<div class="shell">
	<header class="top">
		<button
			class="icon menu"
			aria-label="Open library"
			onclick={() => (reader.sidebarOpen = true)}
		>
			<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
		</button>
		<a class="brand" href="/">
			<svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true"><rect x="1" y="1" width="24" height="24" rx="5" fill="none" stroke="var(--accent)" stroke-width="1.6" /><path d="M13 6v14" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" /><circle cx="13" cy="6" r="1.8" fill="var(--accent)" /></svg>
			<span class="mono">ironrod</span>
		</a>
		{#if reader.current}
			<nav class="crumbs mono" aria-label="Breadcrumb">
				<span>~/{reader.current.volume}</span><span aria-hidden="true">/</span><span
					>{reader.current.book}</span
				><span aria-hidden="true">/</span><span class="here">{reader.current.chapter}</span>
			</nav>
		{/if}
	</header>

	<div class="body">
		<Sidebar volumes={data.volumes} />
		<main class="main">
			{@render children()}
		</main>
	</div>

	<StatusBar />
</div>

<style>
	.shell {
		height: 100dvh;
		display: flex;
		flex-direction: column;
	}
	.top {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 0 20px;
		height: 56px;
		flex: 0 0 56px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-raised);
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--text);
		text-decoration: none;
		font-weight: 600;
		font-size: 15px;
		letter-spacing: 0.04em;
	}
	.crumbs {
		display: flex;
		gap: 8px;
		font-size: 13px;
		color: var(--text-faint);
		min-width: 0;
		overflow: hidden;
		white-space: nowrap;
	}
	.here { color: var(--text); }
	.icon {
		all: unset;
		box-sizing: border-box;
		display: none;
		width: 40px;
		height: 40px;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text-muted);
		cursor: pointer;
	}
	.body {
		flex: 1;
		display: flex;
		min-height: 0;
	}
	.main {
		flex: 1;
		min-width: 0;
		overflow-y: auto;
	}
	@media (max-width: 900px) {
		.icon.menu { display: inline-flex; }
		.top { padding: 0 12px; gap: 12px; }
	}
	@media (max-width: 520px) {
		.crumbs { display: none; }
	}
</style>
