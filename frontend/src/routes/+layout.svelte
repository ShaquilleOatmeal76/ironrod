<script>
	import '@fontsource-variable/inter';
	import '@fontsource-variable/jetbrains-mono';
	import '@fontsource-variable/source-serif-4';
	import '../app.css';

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import Sidebar from '#lib/components/Sidebar.svelte';
	import StatusBar from '#lib/components/StatusBar.svelte';
	import SuggestPopup from '#lib/components/SuggestPopup.svelte';
	import CommandPalette from '#lib/components/CommandPalette.svelte';
	import ShortcutsHelp from '#lib/components/ShortcutsHelp.svelte';
	import MobileNav from '#lib/components/MobileNav.svelte';
	import { reader, lastRead, install, watchInstall, promptInstall } from '#lib/reader.svelte.js';
	import { palette, openPalette, registerCommands } from '#lib/commands.svelte.js';
	import { api, chapterHref } from '#lib/api.js';

	let { data, children } = $props();

	function backToReading() {
		const l = lastRead();
		goto(chapterHref(l.volume, l.book, l.chapter));
	}

	// Commands that work on every page.
	$effect(() =>
		registerCommands([
			{ id: 'go-notes', title: 'Go to all notes', group: 'go', keys: 'g n', run: () => goto('/notes') },
			{ id: 'go-search', title: 'Open search page', group: 'go', keys: 'g s', run: () => goto('/search') },
			{ id: 'go-read', title: 'Back to reading', group: 'go', keys: 'g r', run: backToReading },
			{ id: 'new-note', title: 'New note (not tied to a verse)', group: 'notes', run: () => goto('/notes#new') },
			{ id: 'go-plans', title: 'Plans & today\u2019s reading', group: 'go', keys: 'g p', run: () => goto('/plans') },
			{ id: 'go-library', title: 'Talks & lessons library', hint: 'conference byu come follow me import', group: 'go', keys: 'g t', run: () => goto('/library') },
			{ id: 'go-split', title: 'Split view: scripture + talk', group: 'go', keys: 'g v', run: () => goto('/split') },
			{ id: 'go-graph', title: 'Study graph', group: 'go', keys: 'g g', run: () => goto('/graph') },
			{ id: 'new-plan', title: 'Start a reading plan', group: 'go', run: () => goto('/plans') },
			{ id: 'library', title: 'Open library', group: 'go', run: () => (reader.sidebarOpen = true), when: () => window.innerWidth <= 900 },
			{ id: 'install', title: 'Install Iron Rod as an app', group: 'help', run: promptInstall, when: () => !!install.prompt },
			{ id: 'help', title: 'Show keyboard shortcuts', group: 'help', keys: '?', run: () => (palette.help = true) },
			...data.volumes.map((v) => ({
				id: `vol-${v.slug}`,
				title: `Open ${v.title}`,
				group: 'go',
				hint: v.short_title,
				run: () => goto(chapterHref(v.slug, v.books[0].slug, 1))
			}))
		])
	);

	// Global keys. ⌘K / Ctrl+K works even while typing; the rest don't.
	let gPressed = 0;
	function onKey(e) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			palette.open ? (palette.open = false) : openPalette();
			return;
		}
		const t = /** @type {HTMLElement} */ (e.target);
		if (e.metaKey || e.ctrlKey || e.altKey || palette.open || palette.help) return;
		if (t.closest('input, textarea, select, [contenteditable="true"]')) return;
		if (e.key === '/') {
			e.preventDefault();
			openPalette();
		} else if (e.key === '?') {
			palette.help = true;
		} else if (e.key === 'g' && !(Date.now() - gPressed < 800)) {
			gPressed = Date.now();
			palette.gAt = gPressed;
		} else if (Date.now() - gPressed < 800) {
			gPressed = 0;
			if (e.key === 'n') goto('/notes');
			else if (e.key === 's') goto('/search');
			else if (e.key === 'p') goto('/plans');
			else if (e.key === 't') goto('/library');
			else if (e.key === 'v') goto('/split');
			else if (e.key === 'g') goto('/graph');
			else if (e.key === 'r') backToReading();
		}
	}

	// Ping the server now and then so the status bar can show "offline".
	onMount(() => {
		watchInstall();
		const check = () =>
			api.health().then(
				() => (reader.online = true),
				() => (reader.online = false)
			);
		const id = setInterval(check, 30000);
		return () => clearInterval(id);
	});
</script>

<svelte:window onkeydown={onKey} />

<div class="shell">
	<header class="top">
		<button class="icon menu" aria-label="Open library" onclick={() => (reader.sidebarOpen = true)}>
			<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
		</button>
		<a class="brand" href="/">
			<svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true"><rect x="1" y="1" width="24" height="24" rx="5" fill="none" stroke="var(--accent)" stroke-width="1.6" /><path d="M13 6v14" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" /><circle cx="13" cy="6" r="1.8" fill="var(--accent)" /></svg>
			<span class="mono">ironrod</span>
		</a>
		{#if reader.current}
			<nav class="crumbs mono" aria-label="Breadcrumb">
				<span>~/{reader.current.volume}</span><span aria-hidden="true">/</span><span>{reader.current.book}</span><span aria-hidden="true">/</span><span class="here">{reader.current.chapter}</span>
			</nav>
		{/if}
		<span class="grow"></span>
		<button class="trigger" onclick={() => openPalette()}>
			<span class="mono prompt" aria-hidden="true">&gt;</span>
			<span class="label">Go to, search notes, run a command…</span>
			<span class="mono kbd">⌘K</span>
		</button>
		<button class="icon search" aria-label="Search" onclick={() => openPalette()}>
			<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
		</button>
	</header>

	<div class="body">
		<Sidebar volumes={data.volumes} />
		<main class="main">
			{@render children()}
		</main>
	</div>

	<StatusBar />
	<MobileNav />
</div>

<SuggestPopup />
<CommandPalette />
<ShortcutsHelp />

<style>
	.shell { height: 100dvh; display: flex; flex-direction: column; }
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
	.grow { flex: 1; }
	.trigger {
		display: flex;
		align-items: center;
		gap: 10px;
		width: min(380px, 40vw);
		height: 40px;
		padding: 0 12px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		color: var(--text-faint);
		font: 14px var(--font-ui);
		text-align: left;
		cursor: pointer;
	}
	.trigger:hover { border-color: var(--border-strong); color: var(--text-muted); }
	.trigger .label { flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
	.prompt { color: var(--accent); }
	.kbd { font-size: 12px; border: 1px solid var(--border-strong); border-radius: 4px; padding: 1px 6px; }
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
	.body { flex: 1; display: flex; min-height: 0; }
	.main { flex: 1; min-width: 0; overflow-y: auto; }
	@media (max-width: 900px) {
		.icon.menu { display: inline-flex; }
		.top { padding: 0 12px; gap: 12px; }
	}
	@media (max-width: 700px) {
		.trigger { display: none; }
		.icon.search { display: inline-flex; }
	}
	@media (max-width: 520px) {
		.crumbs { display: none; }
	}
</style>
