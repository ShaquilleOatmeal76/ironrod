<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.js';
	import { reader } from '#lib/reader.svelte.js';
	import NoteCard from '#lib/components/NoteCard.svelte';
	import NoteEditor from '#lib/components/NoteEditor.svelte';

	const tag = $derived(page.url.searchParams.get('tag') ?? '');
	let q = $state(page.url.searchParams.get('q') ?? '');
	let notes = $state(/** @type {any[]} */ ([]));
	let tags = $state(/** @type {any[]} */ ([]));
	let loading = $state(true);
	let reload = $state(0);
	let timer;

	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});

	// Re-query when the tag filter, search text or data changes.
	$effect(() => {
		const params = { tag, q: q.trim(), limit: 200 };
		reload;
		clearTimeout(timer);
		timer = setTimeout(async () => {
			loading = true;
			try {
				notes = await api.notes(params);
			} finally {
				loading = false;
			}
		}, 150);
	});

	$effect(() => {
		reload;
		api.tags().then((t) => (tags = t));
	});

	function setTag(t) {
		const url = new URL(page.url.href);
		if (t && t !== tag) url.searchParams.set('tag', t);
		else url.searchParams.delete('tag');
		goto(url, { reset: false });
	}

	async function addFree(html) {
		await api.createNote(html);
		reload++;
	}
</script>

<svelte:head><title>Notes · Iron Rod</title></svelte:head>

<div class="wrap">
	<header class="top">
		<h1>Notes</h1>
		<span class="count mono">{loading ? '…' : `${notes.length} ${notes.length === 1 ? 'note' : 'notes'}`}</span>
	</header>

	<label class="search">
		<span class="sr-only">Search notes</span>
		<span class="mono prompt" aria-hidden="true">/</span>
		<input type="search" bind:value={q} placeholder="search your notes…" />
	</label>

	{#if tags.length}
		<div class="tags" aria-label="Filter by tag">
			{#each tags as t}
				<button class="tag mono" class:on={t.name === tag} aria-pressed={t.name === tag} onclick={() => setTag(t.name)}>
					#{t.name} <span class="n">{t.count}</span>
				</button>
			{/each}
			{#if tag}<button class="tag mono clear" onclick={() => setTag('')}>clear ×</button>{/if}
		</div>
	{/if}

	<details class="free">
		<summary class="mono">+ new note (not tied to a verse)</summary>
		<NoteEditor onsave={addFree} saveLabel="Save note" />
	</details>

	<div class="list">
		{#each notes as note (note.id)}
			<NoteCard {note} showAnchor onchanged={() => reload++} />
		{/each}
		{#if !loading && notes.length === 0}
			<p class="empty">
				{q || tag ? 'No notes match.' : 'No notes yet. Open a chapter, select a verse and press n.'}
			</p>
		{/if}
	</div>
</div>

<style>
	.wrap { max-width: 760px; margin: 0 auto; padding: 36px 24px 80px; display: flex; flex-direction: column; gap: 16px; }
	.top { display: flex; align-items: baseline; gap: 12px; }
	h1 { margin: 0; font-family: var(--font-scripture); font-weight: 600; font-size: 36px; }
	.count { color: var(--text-faint); font-size: 12px; }
	.search {
		display: flex; align-items: center; gap: 10px; height: 46px; padding: 0 14px;
		border: 1px solid var(--border-strong); border-radius: var(--radius); background: var(--surface);
	}
	.search:focus-within { border-color: var(--accent-line); }
	.search input { flex: 1; min-width: 0; background: none; border: 0; outline: none; color: var(--text); font: 15px var(--font-ui); }
	.prompt { color: var(--accent); }
	.tags { display: flex; flex-wrap: wrap; gap: 6px; }
	.tag {
		height: 30px; padding: 0 10px; border-radius: 4px; border: 1px solid var(--border);
		background: #1a2029; color: var(--text-muted); font-size: 12px; cursor: pointer;
	}
	.tag.on { border-color: var(--accent-line); color: var(--accent); background: var(--accent-dim); }
	.tag .n { color: var(--text-faint); }
	.tag.clear { background: transparent; }
	.free summary { cursor: pointer; color: var(--text-faint); font-size: 12px; padding: 6px 0 10px; }
	.free summary:hover { color: var(--text); }
	.list { display: flex; flex-direction: column; gap: 10px; }
	.empty { color: var(--text-faint); }
</style>
