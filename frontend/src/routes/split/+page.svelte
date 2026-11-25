<script>
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { tick } from 'svelte';
	import { api, refHref, paraHref } from '#lib/api.js';
	import { reader } from '#lib/reader.svelte.js';
	import { palette } from '#lib/commands.svelte.js';

	// Split view: scripture on the left, a talk or lesson on the right.
	// Select verse(s) and a paragraph, then link them.

	let refInput = $state(page.url.searchParams.get('ref') ?? 'Alma 32');
	let chapter = $state(/** @type {any} */ (null));
	let ann = $state(/** @type {Record<string, any>} */ ({}));
	let vStart = $state(/** @type {number|null} */ (null));
	let vEnd = $state(/** @type {number|null} */ (null));
	let refError = $state('');

	const initialDoc = page.url.searchParams.get('doc');
	let docId = $state(initialDoc);
	let doc = $state(/** @type {any} */ (null));
	let paraPos = $state(Number(page.url.searchParams.get('p')) || null);
	let docQuery = $state('');
	let docHits = $state(/** @type {any[]} */ ([]));
	let recent = $state(/** @type {any[]} */ ([]));

	let labels = $state(['related']);
	let label = $state('related');
	let toast = $state('');
	const vEls = /** @type {Record<number, HTMLElement>} */ ({});
	const pEls = /** @type {Record<number, HTMLElement>} */ ({});

	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});
	api.linkLabels().then((l) => (labels = l), () => {});

	async function openRef(e) {
		e?.preventDefault();
		refError = '';
		try {
			const r = await api.resolveRef(refInput);
			chapter = await api.chapter(r.volume, r.book, r.chapter);
			ann = await api.annotations(r.volume, r.book, r.chapter);
			refInput = `${chapter.book_title} ${chapter.chapter}`;
			vStart = vEnd = r.verse && r.end_verse_id === r.start_verse_id ? r.verse : null;
			syncUrl();
			await tick();
			if (vStart) vEls[vStart]?.scrollIntoView({ block: 'center' });
		} catch {
			refError = 'couldn’t find that chapter';
		}
	}
	openRef();

	async function step(ref) {
		if (!ref) return;
		refInput = `${ref.book_title} ${ref.chapter}`;
		await openRef();
	}

	async function openDoc(id) {
		docId = String(id);
		doc = await api.doc(id);
		docQuery = '';
		docHits = [];
		syncUrl();
		await tick();
		if (paraPos) pEls[paraPos]?.scrollIntoView({ block: 'center' });
	}
	if (initialDoc) openDoc(initialDoc);
	else api.library().then(async (lib) => {
		const first = lib.flatMap((g) => g.collections).slice(0, 3);
		const lists = await Promise.all(first.map((c) => api.collection(c.id)));
		recent = lists.flatMap((l) => l.docs.slice(0, 4));
	});

	let timer;
	$effect(() => {
		const q = docQuery.trim();
		clearTimeout(timer);
		if (!q) return void (docHits = []);
		timer = setTimeout(async () => {
			const r = await api.search(q, { kinds: 'talks', limit: 20 });
			const seen = new Set();
			docHits = r.talks.items.filter((h) => !seen.has(h.doc_id) && seen.add(h.doc_id)).slice(0, 8);
		}, 200);
	});

	function syncUrl() {
		const url = new URL(page.url.href);
		if (chapter) url.searchParams.set('ref', `${chapter.book_title} ${chapter.chapter}`);
		if (docId) url.searchParams.set('doc', docId);
		paraPos ? url.searchParams.set('p', String(paraPos)) : url.searchParams.delete('p');
		replaceState(url, {});
	}

	function pickVerse(n, e) {
		if (e.shiftKey && vStart) {
			vEnd = n;
			if (vEnd < vStart) [vStart, vEnd] = [vEnd, vStart];
		} else if (vStart === n && vEnd === n) {
			vStart = vEnd = null;
		} else {
			vStart = vEnd = n;
		}
	}
	function pickPara(pos) {
		paraPos = paraPos === pos ? null : pos;
		syncUrl();
	}

	const verseLabel = $derived(
		chapter && vStart ? `${chapter.book_title === 'Doctrine and Covenants' ? 'D&C' : chapter.book_title} ${chapter.chapter}:${vStart}${vEnd && vEnd !== vStart ? '–' + vEnd : ''}` : null
	);
	const para = $derived(doc && paraPos ? doc.paras.find((p) => p.position === paraPos) : null);

	async function link() {
		if (!chapter || !vStart || !para) return;
		const start = chapter.verses[vStart - 1].id;
		const end = chapter.verses[(vEnd ?? vStart) - 1].id;
		try {
			await api.createParaLink(para.id, { start, end, label });
			toast = `linked ${verseLabel} ↔ ¶${para.position}`;
			setTimeout(() => (toast = ''), 2000);
			[ann, doc] = await Promise.all([api.annotations(chapter.volume, chapter.book, chapter.chapter), api.doc(doc.id)]);
		} catch (e) {
			toast = e.message;
		}
	}

	function onKey(e) {
		const t = /** @type {HTMLElement} */ (e.target);
		if (e.metaKey || e.ctrlKey || e.altKey || palette.open || palette.help) return;
		if (Date.now() - palette.gAt < 800) return;
		if (t.closest('input, textarea, select')) return;
		if (e.key === 'Enter' && verseLabel && para) link();
		else if (e.key === ']') step(chapter?.next);
		else if (e.key === '[') step(chapter?.prev);
	}
</script>

<svelte:window onkeydown={onKey} />
<svelte:head><title>Split view · Iron Rod</title></svelte:head>

<div class="split">
	<section class="pane" aria-label="Scripture">
		<form class="bar" onsubmit={openRef}>
			<button type="button" class="nav" aria-label="Previous chapter" disabled={!chapter?.prev} onclick={() => step(chapter?.prev)}>‹</button>
			<label class="field"><span class="sr-only">Chapter</span><span class="mono prompt" aria-hidden="true">§</span>
				<input bind:value={refInput} placeholder="alma 32" autocomplete="off" /></label>
			<button type="button" class="nav" aria-label="Next chapter" disabled={!chapter?.next} onclick={() => step(chapter?.next)}>›</button>
		</form>
		{#if refError}<p class="err mono">{refError}</p>{/if}
		<div class="scroll">
			{#if chapter}
				<h2 class="ptitle">{chapter.book_title} {chapter.chapter}</h2>
				{#each chapter.verses as v (v.id)}
					{@const on = vStart && v.number >= vStart && v.number <= (vEnd ?? vStart)}
					<button class="item" class:on bind:this={vEls[v.number]} aria-pressed={!!on} onclick={(e) => pickVerse(v.number, e)}>
						<span class="num mono">{v.number}</span><span class="txt">{v.text}</span>
						{#if ann[v.number]?.links}<span class="dot" title="{ann[v.number].links} links" aria-hidden="true"></span>{/if}
					</button>
				{/each}
			{/if}
		</div>
	</section>

	<section class="pane" aria-label="Talk or lesson">
		<div class="bar">
			<label class="field"><span class="sr-only">Find a talk</span><span class="mono prompt talk" aria-hidden="true">¶</span>
				<input bind:value={docQuery} placeholder={doc ? doc.title : 'find a talk by words in it…'} autocomplete="off" /></label>
		</div>
		<div class="scroll">
			{#if docHits.length}
				<ul class="hits">
					{#each docHits as h}
						<li><button class="hit" onclick={() => openDoc(h.doc_id)}><span class="t">{h.title}</span><span class="m">{h.author ?? ''}</span></button></li>
					{/each}
				</ul>
			{:else if doc}
				<h2 class="ptitle">{doc.title}</h2>
				{#if doc.author}<p class="by">{doc.author}</p>{/if}
				{#each doc.paras as p (p.id)}
					{#if p.kind === 'h2' || p.kind === 'h3'}
						<h3 class="sec">{p.text}</h3>
					{:else}
						<button class="item para" class:on={paraPos === p.position} bind:this={pEls[p.position]} aria-pressed={paraPos === p.position} onclick={() => pickPara(p.position)}>
							<span class="num mono">{p.position}</span><span class="txt">{p.text}</span>
							{#if p.links}<span class="dot" title="{p.links} links" aria-hidden="true"></span>{/if}
						</button>
					{/if}
				{/each}
			{:else}
				<p class="muted">Search for a talk above{recent.length ? ', or pick one:' : '. Import talks from the library first.'}</p>
				<ul class="hits">
					{#each recent as d}<li><button class="hit" onclick={() => openDoc(d.id)}><span class="t">{d.title}</span><span class="m">{d.author ?? d.date_label ?? ''}</span></button></li>{/each}
				</ul>
				{#if !recent.length}<a class="mono" href="/library">open library →</a>{/if}
			{/if}
		</div>
	</section>
</div>

<div class="linkbar" role="region" aria-label="Link selection">
	<span class="sel mono" class:ready={!!verseLabel}>{verseLabel ?? 'select verse(s) — shift-click for a range'}</span>
	<span class="arrow" aria-hidden="true">↔</span>
	<span class="sel mono talk" class:ready={!!para}>{para ? `¶${para.position} ${doc.title}` : 'select a paragraph'}</span>
	<label class="sr-only" for="lbl">Relationship</label>
	<select id="lbl" bind:value={label}>{#each labels as l}<option value={l}>{l}</option>{/each}</select>
	<button class="go" disabled={!verseLabel || !para} onclick={link}>Link <span class="mono">↵</span></button>
	{#if verseLabel && chapter}<a class="mono open" href={refHref({ volume: chapter.volume, book: chapter.book, chapter: chapter.chapter, verse: vStart })}>open verse</a>{/if}
	{#if para}<a class="mono open" href={paraHref({ doc_id: doc.id, position: para.position })}>open ¶</a>{/if}
</div>
{#if toast}<div class="toast mono" role="status">{toast}</div>{/if}

<style>
	.split { display: grid; grid-template-columns: 1fr 1fr; height: calc(100% - 58px); min-height: 0; }
	.pane { display: flex; flex-direction: column; min-height: 0; border-right: 1px solid var(--border); }
	.bar { display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid var(--border); background: var(--bg-raised); }
	.field { flex: 1; display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border: 1px solid var(--border-strong); border-radius: var(--radius); background: var(--surface); }
	.field input { flex: 1; min-width: 0; background: none; border: 0; outline: none; color: var(--text); font: 14px var(--font-mono); }
	.prompt { color: var(--hl-doctrine); }
	.prompt.talk { color: var(--hl-question); }
	.nav { width: 40px; height: 40px; border-radius: var(--radius); border: 1px solid var(--border); background: none; color: var(--text-faint); font-size: 18px; cursor: pointer; }
	.nav:disabled { opacity: 0.3; }
	.scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 16px 40px; }
	.ptitle { font-family: var(--font-scripture); font-size: 24px; margin: 4px 8px 12px; }
	.by { margin: -6px 8px 14px; color: var(--text-muted); font-size: 14px; }
	.sec { font-family: var(--font-scripture); font-size: 18px; margin: 18px 8px 6px 42px; }
	.item { all: unset; box-sizing: border-box; width: 100%; display: flex; gap: 12px; padding: 8px 10px; border-radius: 6px; cursor: pointer; position: relative; }
	.item:hover { background: #0f1318; }
	.item.on { background: #11171c; outline: 1px solid var(--accent-line); }
	.item.para.on { background: #14121c; outline-color: #4a3766; }
	.item:focus-visible { outline: 2px solid var(--accent); }
	.num { flex: 0 0 22px; font-size: 11px; color: var(--text-faint); padding-top: 4px; }
	.txt { flex: 1; font-family: var(--font-scripture); font-size: 16px; line-height: 1.6; }
	.dot { position: absolute; right: 6px; top: 10px; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
	.hits { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
	.hit { all: unset; box-sizing: border-box; width: 100%; display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; }
	.hit:hover { background: var(--surface-hover); }
	.hit .t { font-family: var(--font-scripture); font-size: 16px; }
	.hit .m { font-size: 12px; color: var(--text-faint); }
	.muted { color: var(--text-faint); font-size: 14px; }
	.err { color: var(--hl-promise); font-size: 12px; margin: 6px 14px; }
	.linkbar { height: 58px; display: flex; align-items: center; gap: 10px; padding: 0 14px; border-top: 1px solid var(--border-strong); background: var(--bg-raised); overflow-x: auto; }
	.sel { font-size: 12px; color: var(--text-faint); white-space: nowrap; max-width: 30%; overflow: hidden; text-overflow: ellipsis; }
	.sel.ready { color: var(--hl-doctrine); }
	.sel.talk.ready { color: var(--hl-question); }
	.arrow { color: var(--text-faint); }
	select { height: 36px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius); color: var(--text); font: 12px var(--font-mono); }
	.go { height: 36px; padding: 0 14px; border: 0; border-radius: var(--radius); background: var(--accent); color: var(--accent-ink); font-weight: 600; cursor: pointer; white-space: nowrap; }
	.go:disabled { opacity: 0.35; cursor: default; }
	.open { font-size: 11px; white-space: nowrap; }
	.toast { position: fixed; left: 50%; bottom: 100px; transform: translateX(-50%); z-index: 50; padding: 8px 14px; border-radius: 6px; font-size: 12px; background: var(--surface-hover); border: 1px solid var(--border-strong); }
	@media (max-width: 800px) {
		.split { grid-template-columns: 1fr; grid-template-rows: 1fr 1fr; }
		.pane { border-right: 0; border-bottom: 1px solid var(--border); }
		.linkbar { gap: 8px; }
		.open, .arrow { display: none; }
		.sel { max-width: 34%; }
	}
</style>
