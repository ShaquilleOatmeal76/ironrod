<script>
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { api, refHref } from '#lib/api.js';
	import { reader, refreshProgress } from '#lib/reader.svelte.js';
	import { HIGHLIGHTS, byId, byKey } from '#lib/highlights.js';
	import { palette, registerCommands, pushRecent } from '#lib/commands.svelte.js';
	import ParaPanel from '#lib/components/ParaPanel.svelte';

	let { data } = $props();
	const doc = $derived(data.doc);

	// local copy so highlights update instantly
	let paras = $state(/** @type {any[]} */ ([]));
	$effect(() => {
		paras = data.doc.paras;
	});
	const selectable = $derived(paras.filter((p) => p.kind !== 'h2' && p.kind !== 'h3'));

	let sel = $state(/** @type {number|null} */ (null)); // paragraph position
	const selected = $derived(sel ? paras.find((p) => p.position === sel) : null);
	let sheetOpen = $state(false);
	let noteSignal = $state(0);
	let linkSignal = $state(0);
	let toast = $state('');
	/** @type {HTMLElement} */
	let scroller;
	const els = /** @type {Record<number, HTMLElement>} */ ({});

	const KIND_LABEL = { conference: 'GENERAL CONFERENCE', byu: 'BYU SPEECHES', cfm: 'COME FOLLOW ME' };

	$effect(() => {
		const d = doc;
		reader.current = null;
		reader.verse = null;
		pushRecent({ label: d.title, href: `/doc/${d.id}` });
		const m = page.url.hash.match(/^#p(\d+)$/);
		sel = m ? Number(m[1]) : null;
		sheetOpen = false;
		tick().then(() => (sel ? els[sel]?.scrollIntoView({ block: 'center' }) : scroller?.scrollTo({ top: 0 })));
	});

	function select(pos, toggle = true) {
		sel = toggle && sel === pos ? null : pos;
		if (!sel) sheetOpen = false;
		const url = new URL(page.url.href);
		url.hash = sel ? `p${sel}` : '';
		replaceState(url, {});
	}

	function move(dir) {
		const i = selectable.findIndex((p) => p.position === sel);
		const next = selectable[i < 0 ? (dir > 0 ? 0 : selectable.length - 1) : Math.max(0, Math.min(selectable.length - 1, i + dir))];
		if (next) {
			select(next.position, false);
			els[next.position]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
		}
	}

	async function reload() {
		const fresh = await api.doc(doc.id);
		paras = fresh.paras;
	}

	async function highlight(color) {
		if (!selected) return;
		const p = selected;
		const next = p.highlight === color ? null : color;
		p.highlight = next;
		try {
			await api.setParaHighlight(p.id, next);
		} catch {
			flash('couldn’t save highlight');
			reload();
		}
	}

	async function copy() {
		if (!selected) return;
		try {
			await navigator.clipboard.writeText(`“${selected.text}” — ${doc.author ? doc.author + ', ' : ''}“${doc.title}”`);
			flash('copied');
		} catch {
			flash('copy not allowed here');
		}
	}

	function flash(m) {
		toast = m;
		setTimeout(() => (toast = ''), 1600);
	}

	const splitHref = $derived(`/split?doc=${doc.id}${doc.readings[0] ? `&ref=${encodeURIComponent(doc.readings[0].label.split('–')[0])}` : ''}${sel ? `&p=${sel}` : ''}`);

	$effect(() =>
		registerCommands([
			...HIGHLIGHTS.map((h) => ({ id: `hl-${h.id}`, title: `Highlight as ${h.label}`, hint: `hl ${h.id}`, group: 'verse', keys: h.key, run: () => highlight(h.id), when: () => !!selected })),
			{ id: 'note', title: 'Write a note on this paragraph', group: 'verse', keys: 'n', run: () => ((sheetOpen = true), noteSignal++), when: () => !!selected },
			{ id: 'link', title: 'Link this paragraph to a verse', group: 'verse', keys: 'l', run: () => ((sheetOpen = true), linkSignal++), when: () => !!selected },
			{ id: 'split', title: 'Open in split view', group: 'go', keys: 's', run: () => goto(splitHref) },
			{ id: 'next-doc', title: 'Next talk', group: 'go', keys: ']', run: () => goto(`/doc/${doc.next_id}`), when: () => !!doc.next_id },
			{ id: 'prev-doc', title: 'Previous talk', group: 'go', keys: '[', run: () => goto(`/doc/${doc.prev_id}`), when: () => !!doc.prev_id }
		])
	);

	function onKey(e) {
		const t = /** @type {HTMLElement} */ (e.target);
		if (e.metaKey || e.ctrlKey || e.altKey || palette.open || palette.help) return;
		if (Date.now() - palette.gAt < 800 || e.key === 'g') return; // part of a g-shortcut
		if (t.closest('input, textarea, select, [contenteditable="true"]')) return;
		if (e.key === 'j' || e.key === 'ArrowDown') (e.preventDefault(), move(1));
		else if (e.key === 'k' || e.key === 'ArrowUp') (e.preventDefault(), move(-1));
		else if (e.key === ']' && doc.next_id) goto(`/doc/${doc.next_id}`);
		else if (e.key === '[' && doc.prev_id) goto(`/doc/${doc.prev_id}`);
		else if (e.key === 's') goto(splitHref);
		else if (e.key === 'Escape' && sel) select(sel);
		else if (selected && byKey[e.key]) highlight(byKey[e.key].id);
		else if (selected && e.key === 'n') (e.preventDefault(), (sheetOpen = true), noteSignal++);
		else if (selected && e.key === 'l') (e.preventDefault(), (sheetOpen = true), linkSignal++);
		else if (selected && e.key === 'y') copy();
	}
</script>

<svelte:window onkeydown={onKey} />
<svelte:head><title>{doc.title} · Iron Rod</title></svelte:head>

<div class="page">
	<div class="read-col" bind:this={scroller}>
		<article class="reader">
			<div class="kicker mono">
				<a href="/library?c={doc.collection_id}">{KIND_LABEL[doc.kind]}</a>
				{#if doc.date_label}<span aria-hidden="true">·</span><span>{doc.date_label.toUpperCase()}</span>{/if}
			</div>
			<h1>{doc.title}</h1>
			{#if doc.author}
				<p class="by"><span class="name">{doc.author}</span>{#if doc.author_role}<span class="role">{doc.author_role}</span>{/if}</p>
			{/if}
			{#if doc.readings.length}
				<div class="readings">
					<span class="mono k">READING</span>
					{#each doc.readings as r}<a class="chip mono" href={refHref(r)}>{r.label}</a>{/each}
				</div>
			{/if}
			<div class="actions mono">
				<a href={splitHref}>split view <span class="key">s</span></a>
				<a href={doc.source_url} target="_blank" rel="noopener noreferrer">original ↗</a>
			</div>
			<p class="hint mono">select a paragraph · 1–4 highlight · n note · l link to a verse</p>

			<div class="paras">
				{#each paras as p (p.id)}
					{@const hl = p.highlight ? byId[p.highlight] : null}
					{#if p.kind === 'h2' || p.kind === 'h3'}
						<svelte:element this={p.kind} class="sec">{p.text}</svelte:element>
					{:else}
						<div class="prow" class:selected={sel === p.position} bind:this={els[p.position]} id="p{p.position}">
							<button class="para k-{p.kind}" aria-pressed={sel === p.position} onclick={() => select(p.position)}>
								<span class="num mono">{p.position}</span>
								<span class="text"><span class="mark" class:hl={!!hl} style={hl ? `--c:${hl.color}` : ''}>{p.text}</span></span>
								{#if p.notes || p.links}
									<span class="badges">
										{#if p.links}<span class="badge link mono">{p.links} {p.links === 1 ? 'link' : 'links'}</span>{/if}
										{#if p.notes}<span class="badge note mono">{p.notes === 1 ? 'note' : `${p.notes} notes`}</span>{/if}
									</span>
								{/if}
							</button>
							{#if sel === p.position}
								<div class="tools" role="toolbar" aria-label="Mark up paragraph {p.position}">
									{#each HIGHLIGHTS as h}
										<button class="tool" class:on={p.highlight === h.id} style="--c:{h.color}" aria-pressed={p.highlight === h.id} onclick={() => highlight(h.id)}><span class="sw" aria-hidden="true"></span>{h.label}<span class="mono key">{h.key}</span></button>
									{/each}
									<span class="sep" aria-hidden="true"></span>
									<button class="tool" onclick={() => ((sheetOpen = true), noteSignal++)}>Note<span class="mono key">n</span></button>
									<button class="tool" onclick={() => ((sheetOpen = true), linkSignal++)}>Link<span class="mono key">l</span></button>
									<button class="tool" onclick={copy}>Copy<span class="mono key">y</span></button>
								</div>
							{/if}
						</div>
					{/if}
				{/each}
			</div>

			<div class="foot">
				{#if doc.prev_id}<a class="footlink" href="/doc/{doc.prev_id}"><span class="mono faint">← prev</span>previous</a>{:else}<span></span>{/if}
				{#if doc.next_id}<a class="footlink right" href="/doc/{doc.next_id}"><span class="mono faint">next →</span>next</a>{/if}
			</div>
		</article>
	</div>

	<aside class="side" class:sheet-open={sheetOpen && !!selected}>
		{#if selected}
			{#key selected.id}
				<ParaPanel paraId={selected.id} {noteSignal} {linkSignal} onchanged={reload} onclose={() => (sheetOpen = false)} />
			{/key}
		{:else}
			<div class="empty">
				<p class="mono k">no paragraph selected</p>
				<p>Select a paragraph to write notes or link it to scripture. Or open <a href={splitHref}>split view</a> to read it next to the verses.</p>
			</div>
		{/if}
	</aside>
	{#if toast}<div class="toast mono" role="status">{toast}</div>{/if}
</div>

<style>
	.page { display: flex; height: 100%; min-height: 0; }
	.read-col { flex: 1; min-width: 0; overflow-y: auto; }
	.side { flex: 0 0 400px; width: 400px; min-height: 0; border-left: 1px solid var(--border); background: var(--bg-raised); }
	.empty { padding: 40px 28px; color: var(--text-faint); font-size: 14px; line-height: 1.6; }
	.empty .k { font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; }
	.reader { max-width: 720px; margin: 0 auto; padding: 36px 28px 80px; }
	.kicker { display: flex; gap: 8px; flex-wrap: wrap; font-size: 12px; letter-spacing: 0.14em; color: var(--hl-question); }
	.kicker a { color: inherit; text-decoration: none; }
	h1 { margin: 10px 0 8px; font-family: var(--font-scripture); font-weight: 600; font-size: 36px; line-height: 1.2; letter-spacing: -0.01em; }
	.by { margin: 0; display: flex; flex-direction: column; gap: 2px; }
	.name { font-size: 15px; color: var(--text); }
	.role { font-size: 13px; color: var(--text-faint); }
	.readings { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 14px; }
	.readings .k { font-size: 11px; letter-spacing: 0.12em; color: var(--text-faint); margin-right: 4px; }
	.chip { font-size: 12px; color: var(--hl-doctrine); border: 1px solid #2b3b66; border-radius: 4px; padding: 4px 8px; text-decoration: none; }
	.actions { display: flex; gap: 16px; margin-top: 16px; font-size: 12px; }
	.actions a { text-decoration: none; }
	.key { color: var(--text-faint); border: 1px solid var(--border-strong); border-radius: 3px; padding: 0 4px; }
	.hint { color: var(--text-faint); font-size: 12px; margin: 20px 0 16px; padding-top: 16px; border-top: 1px solid var(--border); }
	.paras { display: flex; flex-direction: column; gap: 2px; }
	.sec { margin: 22px 16px 8px 60px; font-family: var(--font-scripture); font-size: 21px; font-weight: 600; }
	h3.sec { font-size: 18px; color: var(--text-muted); }
	.prow { border-radius: 8px; scroll-margin: 80px; }
	.prow.selected { background: #14121c; outline: 1px solid #4a3766; }
	.para { all: unset; box-sizing: border-box; width: 100%; display: flex; gap: 16px; padding: 12px 16px; border-radius: 8px; cursor: pointer; }
	.prow:not(.selected) .para:hover { background: #0f1318; }
	.para:focus-visible { outline: 2px solid var(--accent); }
	.num { flex: 0 0 28px; font-size: 11px; padding-top: 6px; color: var(--text-faint); }
	.selected .num { color: var(--hl-question); }
	.text { flex: 1; font-family: var(--font-scripture); font-size: 18px; line-height: 1.7; color: var(--text); }
	.k-quote .text { color: var(--text-muted); font-style: italic; padding-left: 14px; border-left: 2px solid var(--border-strong); }
	.k-li .text::before { content: '•'; color: var(--text-faint); margin-right: 10px; }
	.mark.hl { background: color-mix(in srgb, var(--c) 16%, transparent); box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--c) 60%, transparent); border-radius: 2px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
	.badges { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; padding-top: 6px; }
	.badge { font-size: 11px; border-radius: 4px; padding: 2px 6px; white-space: nowrap; border: 1px solid; }
	.badge.link { color: var(--accent); border-color: var(--accent-line); }
	.badge.note { color: var(--hl-promise); border-color: #4a3a1e; }
	.tools { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 0 16px 14px 60px; }
	.tool { height: 34px; padding: 0 10px; border-radius: var(--radius); border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-soft); font-size: 12px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
	.tool.on { border-color: var(--c); }
	.sw { width: 12px; height: 12px; border-radius: 3px; background: var(--c); }
	.tool .key { border: 0; padding: 0; }
	.sep { width: 1px; height: 20px; background: var(--border-strong); margin: 0 4px; }
	.foot { display: flex; justify-content: space-between; margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border); }
	.footlink { display: flex; flex-direction: column; gap: 4px; color: var(--text); text-decoration: none; padding: 8px 0; }
	.footlink.right { text-align: right; }
	.faint { color: var(--text-faint); font-size: 11px; }
	.toast { position: fixed; left: 50%; bottom: 48px; transform: translateX(-50%); z-index: 50; padding: 8px 14px; border-radius: 6px; font-size: 12px; background: var(--surface-hover); border: 1px solid var(--border-strong); }
	@media (max-width: 1100px) {
		.side { position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; width: auto; height: min(72dvh, 640px); border-left: 0; border-top: 1px solid var(--border-strong); border-radius: 16px 16px 0 0; overflow: hidden; box-shadow: 0 -16px 40px rgba(0, 0, 0, 0.5); transform: translateY(105%); transition: transform 0.2s ease; }
		.side.sheet-open { transform: none; }
	}
	@media (max-width: 600px) {
		.reader { padding: 24px 12px 64px; }
		h1 { font-size: 28px; }
		.para { gap: 10px; padding: 10px; }
		.text { font-size: 17px; }
		.tools { padding: 0 10px 12px; }
		.tool { height: 40px; }
		.sec { margin-left: 10px; }
	}
</style>
