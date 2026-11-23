<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, refHref } from '#lib/api.js';
	import { reader } from '#lib/reader.svelte.js';
	import Hits from '#lib/components/Hits.svelte';

	const SCOPES = [
		['all', 'All'],
		['ot', 'Old Testament'],
		['nt', 'New Testament'],
		['bofm', 'Book of Mormon'],
		['dc-testament', 'D&C'],
		['pgp', 'Pearl of Great Price']
	];
	const PAGE = 25;

	let q = $state(page.url.searchParams.get('q') ?? '');
	let scope = $state(page.url.searchParams.get('scope') ?? 'all');
	let res = $state(/** @type {any} */ (null));
	let verses = $state(/** @type {any[]} */ ([]));
	let loading = $state(false);
	let more = $state(false);
	let timer;
	let seq = 0;

	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});

	// Search as you type; keep the URL in sync so results can be bookmarked.
	$effect(() => {
		const query = q.trim();
		const sc = scope;
		clearTimeout(timer);
		const mine = ++seq;
		timer = setTimeout(async () => {
			const url = new URL(page.url.href);
			query ? url.searchParams.set('q', query) : url.searchParams.delete('q');
			sc !== 'all' ? url.searchParams.set('scope', sc) : url.searchParams.delete('scope');
			if (url.search !== page.url.search) goto(url, { replace: true, reset: false });
			if (!query) {
				res = null;
				verses = [];
				return;
			}
			loading = true;
			try {
				const r = await api.search(query, { scope: sc, limit: PAGE });
				if (mine !== seq) return;
				res = r;
				verses = r.verses.items;
			} finally {
				if (mine === seq) loading = false;
			}
		}, 200);
	});

	async function loadMore() {
		more = true;
		try {
			const r = await api.search(q.trim(), { scope, kinds: 'verses', limit: PAGE, offset: verses.length });
			verses = [...verses, ...r.verses.items];
		} finally {
			more = false;
		}
	}

	function when(ts) {
		return new Date(ts.replace(' ', 'T') + 'Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }).toLowerCase();
	}
</script>

<svelte:head><title>{q ? `${q} · ` : ''}Search · Iron Rod</title></svelte:head>

<div class="wrap">
	<h1>Search</h1>

	<label class="search">
		<span class="sr-only">Search scriptures and notes</span>
		<span class="mono prompt" aria-hidden="true">/</span>
		<!-- svelte-ignore a11y_autofocus -->
		<input type="search" bind:value={q} placeholder="words, a phrase in quotes, or a reference…" autofocus />
		{#if loading}<span class="mono faint">…</span>{/if}
	</label>

	<div class="scopes" role="radiogroup" aria-label="Search in">
		{#each SCOPES as [id, label]}
			<button role="radio" aria-checked={scope === id} class:on={scope === id} onclick={() => (scope = id)}>{label}</button>
		{/each}
	</div>

	{#if res}
		{#if res.ref}
			<a class="goto" href={refHref(res.ref)}>
				<span class="mono k">GO TO</span>
				<span class="mono ref">{res.ref.label}</span>
				<span class="txt">{res.ref.text}</span>
			</a>
		{/if}

		{#if res.notes.total}
			<section>
				<h2 class="mono">YOUR NOTES <span class="n">{res.notes.total}</span></h2>
				{#each res.notes.items as n (n.id)}
					<a class="hit" href={n.anchor ? refHref(n.anchor) : `/notes?q=${encodeURIComponent(q)}`}>
						<span class="meta mono">{n.anchor?.label ?? 'note'} · {when(n.updated_at)}{n.tags.length ? ' · ' + n.tags.map((t) => '#' + t).join(' ') : ''}</span>
						<span class="body"><Hits parts={n.parts} /></span>
					</a>
				{/each}
				{#if res.notes.total > res.notes.items.length}
					<a class="all mono" href="/notes?q={encodeURIComponent(q)}">all {res.notes.total} notes →</a>
				{/if}
			</section>
		{/if}

		<section>
			<h2 class="mono">SCRIPTURES <span class="n">{res.verses.total.toLocaleString()}</span></h2>
			{#each verses as v (v.start_verse_id)}
				<a class="hit" href={refHref(v)}>
					<span class="meta mono ref">{v.label}</span>
					<span class="body scripture"><Hits parts={v.parts} /></span>
				</a>
			{/each}
			{#if !res.verses.total}
				<p class="faint">No verses match{scope !== 'all' ? ' in this volume' : ''}.</p>
			{/if}
			{#if verses.length < res.verses.total}
				<button class="more mono" disabled={more} onclick={loadMore}>
					{more ? 'loading…' : `show more (${(res.verses.total - verses.length).toLocaleString()} left)`}
				</button>
			{/if}
		</section>
	{:else if !q.trim()}
		<div class="tips">
			<p class="mono k">TIPS</p>
			<ul>
				<li><span class="mono">faith hope</span> — verses with both words</li>
				<li><span class="mono">"perfect love"</span> — an exact phrase</li>
				<li><span class="mono">believe</span> — also finds believed, believing</li>
				<li><span class="mono">moroni 10:4</span> — jump straight to a verse</li>
				<li>Press <span class="mono">⌘K</span> anywhere for quick search</li>
			</ul>
		</div>
	{/if}
</div>

<style>
	.wrap { max-width: 800px; margin: 0 auto; padding: 36px 24px 80px; display: flex; flex-direction: column; gap: 16px; }
	h1 { margin: 0; font-family: var(--font-scripture); font-weight: 600; font-size: 36px; }
	.search {
		display: flex; align-items: center; gap: 10px; height: 50px; padding: 0 14px;
		border: 1px solid var(--border-strong); border-radius: var(--radius); background: var(--surface);
	}
	.search:focus-within { border-color: var(--accent-line); }
	.search input { flex: 1; min-width: 0; background: none; border: 0; outline: none; color: var(--text); font: 16px var(--font-ui); }
	.prompt { color: var(--accent); }
	.faint { color: var(--text-faint); }
	.scopes { display: flex; flex-wrap: wrap; gap: 6px; }
	.scopes button {
		height: 34px; padding: 0 12px; border-radius: var(--radius); border: 1px solid var(--border);
		background: none; color: var(--text-muted); font-size: 13px; cursor: pointer;
	}
	.scopes button.on { border-color: var(--accent-line); background: var(--accent-dim); color: var(--accent); }
	.goto {
		display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 12px; padding: 14px 16px;
		border: 1px solid var(--accent-line); border-radius: 8px; background: var(--accent-dim); text-decoration: none;
	}
	.goto .k { font-size: 11px; letter-spacing: 0.12em; color: var(--accent); }
	.goto .ref { color: var(--text); font-weight: 600; }
	.goto .txt { flex-basis: 100%; color: var(--text-muted); font-family: var(--font-scripture); font-size: 16px; line-height: 1.5; }
	section { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
	h2 { margin: 0 0 6px; font-size: 12px; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 500; }
	.n { color: var(--text-muted); }
	.hit {
		display: flex; flex-direction: column; gap: 4px; padding: 12px 14px; border-radius: 8px;
		border: 1px solid var(--border); background: var(--surface); text-decoration: none;
	}
	.hit:hover { border-color: var(--border-strong); background: var(--surface-hover); }
	.meta { font-size: 12px; color: var(--text-faint); }
	.meta.ref { color: var(--hl-doctrine); font-weight: 600; }
	.body { color: var(--text-soft); font-size: 14px; line-height: 1.55; }
	.body.scripture { font-family: var(--font-scripture); font-size: 17px; line-height: 1.6; color: var(--text); }
	.all { font-size: 12px; padding: 4px 2px; }
	.more {
		margin-top: 6px; height: 40px; border-radius: var(--radius); border: 1px solid var(--border-strong);
		background: none; color: var(--text-muted); font-size: 12px; cursor: pointer;
	}
	.tips { color: var(--text-muted); font-size: 14px; line-height: 1.9; }
	.tips .k { font-size: 11px; letter-spacing: 0.12em; color: var(--text-faint); margin: 8px 0 0; }
	.tips ul { margin: 4px 0; padding-left: 18px; }
	.tips .mono { color: var(--text); }
</style>
