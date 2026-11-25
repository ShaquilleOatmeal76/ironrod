<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onDestroy } from 'svelte';
	import { api, refHref } from '#lib/api.js';
	import { reader } from '#lib/reader.svelte.js';

	let lib = $state(/** @type {any[]} */ ([]));
	let week = $state(/** @type {any} */ (null));
	let coll = $state(/** @type {any} */ (null));
	let jobs = $state(/** @type {any[]} */ ([]));
	let filter = $state('');
	const cid = $derived(page.url.searchParams.get('c'));
	const thisYear = new Date().getFullYear();

	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});

	async function loadLibrary() {
		[lib, week] = await Promise.all([api.library(), api.cfmWeek().catch(() => null)]);
	}
	loadLibrary();

	$effect(() => {
		const id = cid;
		coll = null;
		if (id) api.collection(id).then((c) => (coll = c));
	});

	const shown = $derived(
		coll && filter.trim()
			? coll.docs.filter((d) => `${d.title} ${d.author ?? ''}`.toLowerCase().includes(filter.trim().toLowerCase()))
			: (coll?.docs ?? [])
	);

	// --- importing ---
	let kind = $state('conference');
	let year = $state(thisYear - (new Date().getMonth() < 4 ? 1 : 0));
	let month = $state(new Date().getMonth() >= 9 ? 10 : 4);
	let cfmYear = $state(thisYear);
	let urls = $state('');
	let importError = $state('');
	let poll;

	async function refreshJobs() {
		jobs = await api.importJobs();
		const running = jobs.some((j) => j.state === 'running');
		if (!running && poll) {
			clearInterval(poll);
			poll = null;
			loadLibrary();
			if (cid) coll = await api.collection(cid);
		}
	}
	refreshJobs();
	onDestroy(() => clearInterval(poll));

	async function startImport(e) {
		e.preventDefault();
		importError = '';
		const body =
			kind === 'conference' ? { kind, year: Number(year), month: Number(month) }
			: kind === 'cfm' ? { kind, year: Number(cfmYear) }
			: { kind, urls: urls.split(/\s+/).filter(Boolean) };
		try {
			await api.startImport(body);
			if (kind === 'byu') urls = '';
			await refreshJobs();
			poll ??= setInterval(refreshJobs, 1500);
		} catch (err) {
			importError = err.message;
		}
	}

	function jobLabel(j) {
		if (j.kind === 'conference') return `${j.params.month === 4 ? 'April' : 'October'} ${j.params.year} conference`;
		if (j.kind === 'cfm') return `Come Follow Me ${j.params.year}`;
		return `${j.params.urls.length} BYU ${j.params.urls.length === 1 ? 'speech' : 'speeches'}`;
	}

	const years = Array.from({ length: thisYear - 1970 }, (_, i) => thisYear - i);
	const empty = $derived(lib.length > 0 && lib.every((g) => g.collections.length === 0));
</script>

<svelte:head><title>{coll ? coll.title : 'Talks & lessons'} · Iron Rod</title></svelte:head>

<div class="wrap">
	{#if coll}
		<a class="back mono" href="/library">← library</a>
		<h1>{coll.title}</h1>
		<label class="search">
			<span class="sr-only">Filter</span><span class="mono prompt" aria-hidden="true">/</span>
			<input bind:value={filter} placeholder="filter by title or speaker…" />
		</label>
		<ol class="docs">
			{#each shown as d (d.id)}
				<li>
					<a class="doc" href="/doc/{d.id}">
						{#if d.kind === 'cfm'}<span class="mono date">{d.date_label}</span>{/if}
						<span class="title">{d.title}</span>
						<span class="meta">{d.kind === 'cfm' ? (d.reading ?? '') : [d.author, d.kind === 'byu' ? d.date_label : null].filter(Boolean).join(' · ')}</span>
					</a>
				</li>
			{/each}
		</ol>
	{:else}
		<h1>Talks & lessons</h1>

		{#if week}
			<a class="week" href="/doc/{week.id}">
				<span class="mono k">THIS WEEK · COME FOLLOW ME · {week.date_label?.toUpperCase()}</span>
				<span class="title">{week.title}</span>
				{#if week.readings.length}
					<span class="chips">{#each week.readings as r}<span class="chip mono">{r.label}</span>{/each}</span>
				{/if}
			</a>
		{/if}

		{#each lib as g (g.kind)}
			{#if g.collections.length}
				<section>
					<h2 class="mono">{g.title.toUpperCase()}</h2>
					<div class="grid">
						{#each g.collections as c (c.id)}
							<a class="coll k-{g.kind}" href="/library?c={c.id}">
								<span class="title">{c.title}</span>
								<span class="mono meta">{c.docs} {g.kind === 'cfm' ? 'lessons' : g.kind === 'byu' ? 'speeches' : 'talks'}</span>
							</a>
						{/each}
					</div>
				</section>
			{/if}
		{/each}
		{#if empty}
			<p class="intro">Nothing imported yet. Bring in a conference, this year's Come Follow Me, or BYU speeches below. Everything is saved on your own server.</p>
		{/if}

		<section class="import" aria-labelledby="imp">
			<h2 id="imp" class="mono">IMPORT</h2>
			<div class="kinds" role="radiogroup" aria-label="What to import">
				{#each [['conference', 'General Conference'], ['cfm', 'Come Follow Me'], ['byu', 'BYU Speeches']] as [k, label]}
					<button role="radio" aria-checked={kind === k} class:on={kind === k} onclick={() => (kind = k)}>{label}</button>
				{/each}
			</div>
			<form onsubmit={startImport}>
				{#if kind === 'conference'}
					<div class="row">
						<label>Year <select bind:value={year}>{#each years as y}<option value={y}>{y}</option>{/each}</select></label>
						<label>Session <select bind:value={month}><option value={4}>April</option><option value={10}>October</option></select></label>
					</div>
					<p class="note">About 35 talks. Takes a minute or two; it waits a second between requests to be polite.</p>
				{:else if kind === 'cfm'}
					<div class="row">
						<label>Year <select bind:value={cfmYear}>{#each years.filter((y) => y >= 2023).concat(thisYear + 1).sort((a, b) => b - a) as y}<option value={y}>{y}</option>{/each}</select></label>
					</div>
					<p class="note">Imports every weekly lesson with its dates and reading, so it can drive a Come Follow Me plan.</p>
				{:else}
					<label class="full">Speech links (one per line)
						<textarea bind:value={urls} rows="4" placeholder="https://speeches.byu.edu/talks/speaker-name/speech-title/"></textarea>
					</label>
				{/if}
				{#if importError}<p class="err" role="alert">{importError}</p>{/if}
				<button class="go" disabled={jobs.some((j) => j.state === 'running' && j.kind === kind)}>Import</button>
			</form>

			{#if jobs.length}
				<ul class="jobs">
					{#each jobs as j (j.id)}
						<li class="job s-{j.state}">
							<div class="top"><span>{jobLabel(j)}</span><span class="mono st">{j.state === 'running' ? `${j.done}/${j.total || '…'}` : j.state === 'done' ? `✓ ${j.added} new` : 'failed'}</span></div>
							{#if j.state === 'running'}
								<div class="bar"><div style="width:{j.total ? (100 * j.done) / j.total : 4}%"></div></div>
								<div class="mono msg">{j.message}</div>
							{:else if j.error}
								<div class="mono msg err">{j.error}</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
			<p class="fine">Talks and lessons are © Intellectual Reserve, Inc. and BYU. Iron Rod keeps them on your server for personal study and never puts them in the code repo.</p>
		</section>
	{/if}
</div>

<style>
	.wrap { max-width: 880px; margin: 0 auto; padding: 36px 24px 80px; display: flex; flex-direction: column; gap: 18px; }
	h1 { margin: 0; font-family: var(--font-scripture); font-weight: 600; font-size: 36px; }
	h2 { margin: 0 0 10px; font-size: 12px; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 500; }
	.back { font-size: 12px; text-decoration: none; }
	.intro { color: var(--text-muted); margin: 0; }
	.week { display: flex; flex-direction: column; gap: 6px; padding: 18px; border-radius: 10px; border: 1px solid var(--accent-line); background: var(--accent-dim); text-decoration: none; }
	.week .k { font-size: 11px; letter-spacing: 0.1em; color: var(--accent); }
	.week .title { font-family: var(--font-scripture); font-size: 22px; color: var(--text); }
	.chips { display: flex; flex-wrap: wrap; gap: 6px; }
	.chip { font-size: 12px; color: var(--hl-doctrine); border: 1px solid #2b3b66; border-radius: 4px; padding: 3px 8px; }
	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
	.coll { display: flex; flex-direction: column; gap: 6px; padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); text-decoration: none; border-left: 3px solid var(--c, var(--border-strong)); }
	.coll:hover { background: var(--surface-hover); }
	.k-conference { --c: var(--hl-question); }
	.k-cfm { --c: var(--accent); }
	.k-byu { --c: var(--hl-doctrine); }
	.coll .title { color: var(--text); font-size: 15px; }
	.coll .meta { font-size: 11px; color: var(--text-faint); }
	.search { display: flex; align-items: center; gap: 10px; height: 44px; padding: 0 14px; border: 1px solid var(--border-strong); border-radius: var(--radius); background: var(--surface); }
	.search input { flex: 1; background: none; border: 0; outline: none; color: var(--text); font: 15px var(--font-ui); }
	.prompt { color: var(--accent); }
	.docs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
	.doc { display: flex; flex-direction: column; gap: 3px; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); text-decoration: none; }
	.doc:hover { background: var(--surface-hover); border-color: var(--border-strong); }
	.doc .date { font-size: 11px; color: var(--accent); }
	.doc .title { color: var(--text); font-family: var(--font-scripture); font-size: 17px; }
	.doc .meta { color: var(--text-faint); font-size: 13px; }
	.import { border-top: 1px solid var(--border); padding-top: 22px; display: flex; flex-direction: column; gap: 12px; }
	.kinds { display: flex; flex-wrap: wrap; gap: 6px; }
	.kinds button { height: 36px; padding: 0 12px; border-radius: var(--radius); border: 1px solid var(--border); background: none; color: var(--text-muted); font-size: 13px; cursor: pointer; }
	.kinds button.on { border-color: var(--accent-line); background: var(--accent-dim); color: var(--accent); }
	form { display: flex; flex-direction: column; gap: 10px; }
	.row { display: flex; flex-wrap: wrap; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-faint); font-family: var(--font-mono); }
	label.full { width: 100%; }
	select, textarea { background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius); color: var(--text); font: 14px var(--font-ui); padding: 8px 10px; min-width: 140px; }
	select { height: 40px; }
	textarea { font-family: var(--font-mono); font-size: 13px; resize: vertical; }
	.note { margin: 0; font-size: 13px; color: var(--text-faint); }
	.go { align-self: flex-start; height: 40px; padding: 0 18px; border: 0; border-radius: var(--radius); background: var(--accent); color: var(--accent-ink); font-weight: 600; cursor: pointer; }
	.go:disabled { opacity: 0.4; cursor: default; }
	.err { color: var(--hl-promise); margin: 0; font-size: 13px; }
	.jobs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
	.job { padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); font-size: 14px; }
	.job .top { display: flex; justify-content: space-between; gap: 12px; }
	.st { font-size: 12px; color: var(--text-faint); }
	.s-done .st { color: var(--accent); }
	.s-error .st { color: var(--hl-promise); }
	.bar { height: 4px; background: var(--border); border-radius: 2px; margin: 8px 0 6px; overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); transition: width 0.3s; }
	.msg { font-size: 11px; color: var(--text-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.fine { font-size: 12px; color: var(--text-faint); margin: 4px 0 0; }
</style>
