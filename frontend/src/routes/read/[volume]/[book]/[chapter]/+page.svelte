<script>
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { chapterHref } from '#lib/api.js';
	import { reader, rememberLast } from '#lib/reader.svelte.js';

	let { data } = $props();
	const ch = $derived(data.chapter);

	/** @type {HTMLElement[]} */
	let verseEls = $state([]);

	// When the chapter changes: publish it to shared state, remember it,
	// and either jump to the verse in the URL (#v21) or scroll to the top.
	$effect(() => {
		const c = ch;
		reader.current = { volume: c.volume, book: c.book, book_title: c.book_title, chapter: c.chapter };
		rememberLast(c.volume, c.book, c.chapter);
		const m = page.url.hash.match(/^#v(\d+)$/);
		reader.verse = m ? Number(m[1]) : null;
		tick().then(() => {
			if (reader.verse) scrollToVerse(reader.verse, 'center');
			else document.querySelector('.main')?.scrollTo({ top: 0 });
		});
	});

	/** @param {number} n @param {ScrollLogicalPosition} [block] */
	function scrollToVerse(n, block = 'nearest') {
		verseEls[n - 1]?.scrollIntoView({ block, behavior: 'smooth' });
	}

	function select(n) {
		reader.verse = reader.verse === n ? null : n;
		const url = new URL(page.url.href);
		url.hash = reader.verse ? `v${reader.verse}` : '';
		replaceState(url, {});
	}

	function go(ref) {
		if (ref) goto(chapterHref(ref.volume, ref.book, ref.chapter));
	}

	// Keyboard: j/k move between verses, [ and ] change chapter, esc clears.
	function onKey(e) {
		const t = /** @type {HTMLElement} */ (e.target);
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (t.closest('input, textarea, select, [contenteditable="true"]')) return;
		const last = ch.verses.length;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			select(Math.min((reader.verse ?? 0) + 1, last));
			scrollToVerse(reader.verse);
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			select(Math.max((reader.verse ?? 2) - 1, 1));
			scrollToVerse(reader.verse);
		} else if (e.key === ']') {
			go(ch.next);
		} else if (e.key === '[') {
			go(ch.prev);
		} else if (e.key === 'Escape' && reader.verse) {
			select(reader.verse);
		}
	}
</script>

<svelte:window onkeydown={onKey} />
<svelte:head><title>{ch.book_title} {ch.chapter} · Iron Rod</title></svelte:head>

<article class="reader">
	<div class="head">
		<button
			class="nav"
			aria-label={ch.prev ? `Previous: ${ch.prev.book_title} ${ch.prev.chapter}` : 'No previous chapter'}
			disabled={!ch.prev}
			onclick={() => go(ch.prev)}>‹</button
		>
		<div class="titles">
			<div class="kicker mono">{ch.book_long_title.toUpperCase()}</div>
			<h1>{ch.book_title === 'Doctrine and Covenants' ? 'Section' : 'Chapter'} {ch.chapter}</h1>
		</div>
		<button
			class="nav"
			aria-label={ch.next ? `Next: ${ch.next.book_title} ${ch.next.chapter}` : 'No next chapter'}
			disabled={!ch.next}
			onclick={() => go(ch.next)}>›</button
		>
	</div>
	<p class="hint mono">tap a verse to select · j/k to move</p>

	<ol class="verses">
		{#each ch.verses as v, i (v.id)}
			<li bind:this={verseEls[i]} id="v{v.number}">
				<button class="verse" class:selected={reader.verse === v.number} aria-pressed={reader.verse === v.number} onclick={() => select(v.number)}>
					<span class="num mono">{v.number}</span>
					<span class="text">{v.text}</span>
				</button>
			</li>
		{/each}
	</ol>

	<div class="foot">
		{#if ch.prev}
			<a class="footlink" href={chapterHref(ch.prev.volume, ch.prev.book, ch.prev.chapter)}>
				<span class="mono faint">← prev</span>{ch.prev.book_title} {ch.prev.chapter}
			</a>
		{:else}<span></span>{/if}
		{#if ch.next}
			<a class="footlink right" href={chapterHref(ch.next.volume, ch.next.book, ch.next.chapter)}>
				<span class="mono faint">next →</span>{ch.next.book_title} {ch.next.chapter}
			</a>
		{/if}
	</div>
</article>

<style>
	.reader {
		max-width: 720px;
		margin: 0 auto;
		padding: 36px 28px 80px;
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	.titles { text-align: center; }
	.kicker {
		font-size: 12px;
		letter-spacing: 0.16em;
		color: var(--accent);
	}
	h1 {
		margin: 6px 0 0;
		font-family: var(--font-scripture);
		font-weight: 600;
		font-size: 40px;
		letter-spacing: -0.01em;
	}
	.nav {
		width: 44px;
		height: 44px;
		border-radius: var(--radius);
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-faint);
		font-size: 20px;
		cursor: pointer;
	}
	.nav:hover:not(:disabled) { color: var(--text); border-color: var(--border-strong); }
	.nav:disabled { opacity: 0.35; cursor: default; }
	.hint {
		text-align: center;
		color: var(--text-faint);
		font-size: 12px;
		margin: 10px 0 24px;
	}
	.verses {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.verse {
		all: unset;
		box-sizing: border-box;
		width: 100%;
		display: flex;
		gap: 16px;
		padding: 12px 16px;
		border-radius: 8px;
		cursor: pointer;
		scroll-margin: 80px;
	}
	.verse:hover { background: #0f1318; }
	.verse.selected {
		background: #11171c;
		outline: 1px solid var(--accent-line);
	}
	.verse:focus-visible { outline: 2px solid var(--accent); }
	.num {
		flex: 0 0 28px;
		font-size: 13px;
		font-weight: 600;
		padding-top: 5px;
		color: var(--text-faint);
	}
	.selected .num { color: var(--accent); }
	.text {
		flex: 1;
		font-family: var(--font-scripture);
		font-size: 19px;
		line-height: 1.7;
		color: var(--text);
	}
	.foot {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		margin-top: 48px;
		padding-top: 20px;
		border-top: 1px solid var(--border);
	}
	.footlink {
		display: flex;
		flex-direction: column;
		gap: 4px;
		color: var(--text);
		text-decoration: none;
		font-size: 15px;
		padding: 8px 0;
	}
	.footlink.right { text-align: right; }
	.footlink:hover { color: var(--accent); }
	.faint { color: var(--text-faint); font-size: 11px; }

	@media (max-width: 600px) {
		.reader { padding: 24px 12px 64px; }
		h1 { font-size: 30px; }
		.verse { gap: 12px; padding: 10px; }
		.text { font-size: 17px; }
	}
</style>
