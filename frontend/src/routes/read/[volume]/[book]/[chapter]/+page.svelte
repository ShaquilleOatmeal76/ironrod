<script>
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { api, chapterHref } from '#lib/api.js';
	import { reader, rememberLast } from '#lib/reader.svelte.js';
	import { HIGHLIGHTS, byId, byKey } from '#lib/highlights.js';
	import VersePanel from '#lib/components/VersePanel.svelte';

	let { data } = $props();
	const ch = $derived(data.chapter);

	// Per-verse highlight + counts. Starts from the page load, refreshed after edits.
	let ann = $state(/** @type {Record<string, any>} */ ({}));
	$effect(() => {
		ann = data.annotations;
	});

	/** @type {HTMLElement[]} */
	let verseEls = $state([]);
	/** @type {HTMLElement} */
	let scroller;

	// Small screens show the panel as a bottom sheet, opened on demand.
	let sheetOpen = $state(false);
	let noteSignal = $state(0);
	let linkSignal = $state(0);
	let toast = $state('');

	const selected = $derived(reader.verse ? ch.verses[reader.verse - 1] : null);

	$effect(() => {
		const c = ch;
		reader.current = { volume: c.volume, book: c.book, book_title: c.book_title, chapter: c.chapter };
		rememberLast(c.volume, c.book, c.chapter);
		const m = page.url.hash.match(/^#v(\d+)$/);
		reader.verse = m && Number(m[1]) <= c.verses.length ? Number(m[1]) : null;
		sheetOpen = false;
		tick().then(() => {
			if (reader.verse) scrollToVerse(reader.verse, 'center');
			else scroller?.scrollTo({ top: 0 });
		});
	});

	async function reloadAnnotations() {
		ann = await api.annotations(ch.volume, ch.book, ch.chapter);
	}

	/** @param {number} n @param {ScrollLogicalPosition} [block] */
	function scrollToVerse(n, block = 'nearest') {
		verseEls[n - 1]?.scrollIntoView({ block, behavior: 'smooth' });
	}

	function select(n, toggle = true) {
		reader.verse = toggle && reader.verse === n ? null : n;
		if (!reader.verse) sheetOpen = false;
		const url = new URL(page.url.href);
		url.hash = reader.verse ? `v${reader.verse}` : '';
		replaceState(url, {});
	}

	function go(ref) {
		if (ref) goto(chapterHref(ref.volume, ref.book, ref.chapter));
	}

	async function highlight(color) {
		if (!selected) return;
		const n = reader.verse;
		const current = ann[n]?.highlight ?? null;
		const next = current === color ? null : color;
		// update the screen right away, then save
		ann[n] = { notes: 0, links: 0, ...ann[n], highlight: next };
		try {
			await api.setHighlight(selected.id, selected.id, next);
		} catch {
			flash('couldn’t save highlight');
			reloadAnnotations();
		}
	}

	function openNotes() {
		sheetOpen = true;
		noteSignal++;
	}
	function openLinks() {
		sheetOpen = true;
		linkSignal++;
	}

	async function copyVerse() {
		if (!selected) return;
		const title = ch.book_title === 'Doctrine and Covenants' ? 'D&C' : ch.book_title;
		const text = `“${selected.text}” — ${title} ${ch.chapter}:${selected.number}`;
		try {
			await navigator.clipboard.writeText(text);
			flash('copied');
		} catch {
			flash('copy not allowed here');
		}
	}

	function flash(msg) {
		toast = msg;
		setTimeout(() => (toast = ''), 1600);
	}

	// Keyboard shortcuts (ignored while typing).
	function onKey(e) {
		const t = /** @type {HTMLElement} */ (e.target);
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (t.closest('input, textarea, select, [contenteditable="true"]')) return;
		const last = ch.verses.length;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			select(Math.min((reader.verse ?? 0) + 1, last), false);
			scrollToVerse(reader.verse);
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			select(Math.max((reader.verse ?? 2) - 1, 1), false);
			scrollToVerse(reader.verse);
		} else if (e.key === ']') {
			go(ch.next);
		} else if (e.key === '[') {
			go(ch.prev);
		} else if (e.key === 'Escape' && reader.verse) {
			select(reader.verse);
		} else if (selected && byKey[e.key]) {
			highlight(byKey[e.key].id);
		} else if (selected && e.key === 'n') {
			e.preventDefault();
			openNotes();
		} else if (selected && e.key === 'l') {
			e.preventDefault();
			openLinks();
		} else if (selected && e.key === 'y') {
			copyVerse();
		}
	}
</script>

<svelte:window onkeydown={onKey} />
<svelte:head><title>{ch.book_title} {ch.chapter} · Iron Rod</title></svelte:head>

<div class="page">
	<div class="read-col" bind:this={scroller}>
		<article class="reader">
			<div class="head">
				<button class="nav" aria-label={ch.prev ? `Previous: ${ch.prev.book_title} ${ch.prev.chapter}` : 'No previous chapter'} disabled={!ch.prev} onclick={() => go(ch.prev)}>‹</button>
				<div class="titles">
					<div class="kicker mono">{ch.book_long_title.toUpperCase()}</div>
					<h1>{ch.book_title === 'Doctrine and Covenants' ? 'Section' : 'Chapter'} {ch.chapter}</h1>
				</div>
				<button class="nav" aria-label={ch.next ? `Next: ${ch.next.book_title} ${ch.next.chapter}` : 'No next chapter'} disabled={!ch.next} onclick={() => go(ch.next)}>›</button>
			</div>
			<p class="hint mono">select a verse · 1–4 highlight · n note · l link</p>

			<ol class="verses">
				{#each ch.verses as v, i (v.id)}
					{@const a = ann[v.number]}
					{@const hl = a?.highlight ? byId[a.highlight] : null}
					{@const isSel = reader.verse === v.number}
					<li bind:this={verseEls[i]} id="v{v.number}" class="vrow" class:selected={isSel}>
						<button class="verse" aria-pressed={isSel} onclick={() => select(v.number)}>
							<span class="num mono">{v.number}</span>
							<span class="text"><span class="mark" class:hl={!!hl} style={hl ? `--c:${hl.color}` : ''}>{v.text}</span></span>
							{#if a?.notes || a?.links}
								<span class="badges">
									{#if a.links}<span class="badge link mono">{a.links} {a.links === 1 ? 'link' : 'links'}</span>{/if}
									{#if a.notes}<span class="badge note mono">{a.notes === 1 ? 'note' : `${a.notes} notes`}</span>{/if}
								</span>
							{/if}
						</button>

						{#if isSel}
							<div class="tools" role="toolbar" aria-label="Mark up {ch.book_title} {ch.chapter}:{v.number}">
								{#each HIGHLIGHTS as h}
									<button class="tool" class:on={a?.highlight === h.id} style="--c:{h.color}" aria-pressed={a?.highlight === h.id} onclick={() => highlight(h.id)}>
										<span class="sw" aria-hidden="true"></span>{h.label}<span class="mono key">{h.key}</span>
									</button>
								{/each}
								<span class="sep" aria-hidden="true"></span>
								<button class="tool" onclick={openNotes}>Note<span class="mono key">n</span></button>
								<button class="tool" onclick={openLinks}>Link<span class="mono key">l</span></button>
								<button class="tool" onclick={copyVerse}>Copy<span class="mono key">y</span></button>
							</div>
						{/if}
					</li>
				{/each}
			</ol>

			<div class="foot">
				{#if ch.prev}
					<a class="footlink" href={chapterHref(ch.prev.volume, ch.prev.book, ch.prev.chapter)}><span class="mono faint">← prev</span>{ch.prev.book_title} {ch.prev.chapter}</a>
				{:else}<span></span>{/if}
				{#if ch.next}
					<a class="footlink right" href={chapterHref(ch.next.volume, ch.next.book, ch.next.chapter)}><span class="mono faint">next →</span>{ch.next.book_title} {ch.next.chapter}</a>
				{/if}
			</div>
		</article>
	</div>

	<aside class="side" class:sheet-open={sheetOpen && !!selected}>
		{#if selected}
			{#key selected.id}
				<VersePanel verseId={selected.id} {noteSignal} {linkSignal} onchanged={reloadAnnotations} onclose={() => (sheetOpen = false)} />
			{/key}
		{:else}
			<div class="empty">
				<p class="mono k">no verse selected</p>
				<p>Select a verse to see its notes and links, or press <span class="mono kbd">j</span> to start.</p>
			</div>
		{/if}
	</aside>

	{#if toast}<div class="toast mono" role="status">{toast}</div>{/if}
</div>

<style>
	.page { display: flex; height: 100%; min-height: 0; }
	.read-col { flex: 1; min-width: 0; overflow-y: auto; }
	.side {
		flex: 0 0 400px;
		width: 400px;
		min-height: 0;
		border-left: 1px solid var(--border);
		background: var(--bg-raised);
	}
	.empty { padding: 40px 28px; color: var(--text-faint); font-size: 14px; line-height: 1.6; }
	.empty .k { font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-faint); }
	.kbd { border: 1px solid var(--border-strong); border-radius: 4px; padding: 0 5px; color: var(--text-muted); }

	.reader { max-width: 720px; margin: 0 auto; padding: 36px 28px 80px; }
	.head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
	.titles { text-align: center; }
	.kicker { font-size: 12px; letter-spacing: 0.16em; color: var(--accent); }
	h1 { margin: 6px 0 0; font-family: var(--font-scripture); font-weight: 600; font-size: 40px; letter-spacing: -0.01em; }
	.nav {
		width: 44px; height: 44px; border-radius: var(--radius); border: 1px solid var(--border);
		background: transparent; color: var(--text-faint); font-size: 20px; cursor: pointer;
	}
	.nav:hover:not(:disabled) { color: var(--text); border-color: var(--border-strong); }
	.nav:disabled { opacity: 0.35; cursor: default; }
	.hint { text-align: center; color: var(--text-faint); font-size: 12px; margin: 10px 0 24px; }

	.verses { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
	.vrow { border-radius: 8px; scroll-margin: 80px; }
	.vrow.selected { background: #11171c; outline: 1px solid var(--accent-line); }
	.verse {
		all: unset; box-sizing: border-box; width: 100%;
		display: flex; gap: 16px; padding: 12px 16px; border-radius: 8px; cursor: pointer;
	}
	.vrow:not(.selected) .verse:hover { background: #0f1318; }
	.verse:focus-visible { outline: 2px solid var(--accent); }
	.num { flex: 0 0 28px; font-size: 13px; font-weight: 600; padding-top: 5px; color: var(--text-faint); }
	.selected .num { color: var(--accent); }
	.text { flex: 1; font-family: var(--font-scripture); font-size: 19px; line-height: 1.7; color: var(--text); }
	.mark.hl {
		background: color-mix(in srgb, var(--c) 16%, transparent);
		box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--c) 60%, transparent);
		border-radius: 2px;
		-webkit-box-decoration-break: clone;
		box-decoration-break: clone;
	}
	.badges { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; padding-top: 6px; }
	.badge { font-size: 11px; border-radius: 4px; padding: 2px 6px; white-space: nowrap; border: 1px solid; }
	.badge.link { color: var(--accent); border-color: var(--accent-line); }
	.badge.note { color: var(--hl-promise); border-color: #4a3a1e; }

	.tools { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 0 16px 14px 60px; }
	.tool {
		height: 34px; padding: 0 10px; border-radius: var(--radius);
		border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-soft);
		font-size: 12px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
	}
	.tool:hover { border-color: #3a4452; color: var(--text); }
	.tool.on { border-color: var(--c); }
	.sw { width: 12px; height: 12px; border-radius: 3px; background: var(--c); }
	.key { color: var(--text-faint); }
	.sep { width: 1px; height: 20px; background: var(--border-strong); margin: 0 4px; }

	.foot { display: flex; justify-content: space-between; gap: 16px; margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border); }
	.footlink { display: flex; flex-direction: column; gap: 4px; color: var(--text); text-decoration: none; font-size: 15px; padding: 8px 0; }
	.footlink.right { text-align: right; }
	.footlink:hover { color: var(--accent); }
	.faint { color: var(--text-faint); font-size: 11px; }

	.toast {
		position: fixed; left: 50%; bottom: 48px; transform: translateX(-50%); z-index: 50;
		padding: 8px 14px; border-radius: 6px; font-size: 12px;
		background: var(--surface-hover); border: 1px solid var(--border-strong); color: var(--text);
	}

	/* Below desktop width the panel becomes a bottom sheet. */
	@media (max-width: 1100px) {
		.side {
			position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
			width: auto; height: min(72dvh, 640px);
			border-left: 0; border-top: 1px solid var(--border-strong);
			border-radius: 16px 16px 0 0; overflow: hidden;
			box-shadow: 0 -16px 40px rgba(0, 0, 0, 0.5);
			transform: translateY(105%); transition: transform 0.2s ease;
		}
		.side.sheet-open { transform: none; }
	}
	@media (max-width: 600px) {
		.reader { padding: 24px 12px 64px; }
		h1 { font-size: 30px; }
		.verse { gap: 12px; padding: 10px; }
		.text { font-size: 17px; }
		.tools { padding: 0 10px 12px 10px; }
		.tool { height: 40px; }
	}
</style>
