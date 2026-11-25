<script>
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { api, chapterHref, refHref } from '#lib/api.js';
	import {
		palette,
		closePalette,
		availableCommands,
		matchCommand,
		recentChapters
	} from '#lib/commands.svelte.js';
	import Hits from './Hits.svelte';

	const FILTERS = ['all', 'verses', 'notes', 'commands'];
	let filter = $state('all');
	let input = $state();
	let index = $state(0);
	let res = $state(/** @type {any} */ (null));
	let loading = $state(false);
	let timer;
	let seq = 0;
	let lastFocus = /** @type {HTMLElement|null} */ (null);

	// Open: remember focus, reset, focus the input. Close: restore focus.
	$effect(() => {
		if (palette.open) {
			lastFocus = /** @type {HTMLElement} */ (document.activeElement);
			filter = 'all';
			index = 0;
			tick().then(() => {
				input?.focus();
				input?.select();
			});
		} else {
			lastFocus?.focus?.();
		}
	});

	// Leading ">" means commands only; leading "#" means tags.
	const mode = $derived(
		palette.query.startsWith('>') ? 'commands' : palette.query.startsWith('#') ? 'tags' : filter
	);
	const text = $derived(palette.query.replace(/^[>]/, '').trim());

	// Ask the server (debounced) whenever the text changes.
	$effect(() => {
		const q = text;
		const m = mode;
		clearTimeout(timer);
		if (!palette.open || !q || m === 'commands') {
			res = null;
			loading = false;
			return;
		}
		loading = true;
		const mine = ++seq;
		timer = setTimeout(async () => {
			const kinds =
				m === 'verses' ? 'ref,books,verses' : m === 'notes' ? 'notes,tags,talks' : m === 'tags' ? 'tags' : 'ref,books,verses,notes,tags,talks';
			try {
				const r = await api.search(q, { kinds, limit: m === 'all' ? 5 : 12 });
				if (mine === seq) res = r;
			} catch {
				if (mine === seq) res = null;
			} finally {
				if (mine === seq) loading = false;
			}
		}, 120);
	});

	/** Build the visible, grouped list. Each item has `run`. */
	const groups = $derived.by(() => {
		const out = [];
		const go = (href) => () => goto(href);
		const cmds = availableCommands().filter((c) => matchCommand(c, text));

		if (!text) {
			const recent = recentChapters();
			if (mode === 'all' && recent.length)
				out.push({ title: 'RECENT', items: recent.map((r) => ({ kind: 'recent', icon: '↺', title: r.label, run: go(r.href) })) });
			if (mode === 'all' || mode === 'commands')
				out.push({ title: 'COMMANDS', items: cmds.slice(0, mode === 'commands' ? 50 : 8).map(cmdItem) });
			return out;
		}

		if (mode === 'commands') {
			out.push({ title: 'COMMANDS', items: cmds.map(cmdItem) });
			return out;
		}

		if (res?.ref)
			out.push({ title: 'GO TO', items: [{ kind: 'ref', icon: '§', title: res.ref.label, sub: res.ref.text, run: go(refHref(res.ref)) }] });
		else if (res?.books?.length)
			out.push({
				title: 'GO TO',
				items: res.books.map((b) => ({ kind: 'book', icon: '§', title: b.title, sub: `${b.chapters} ${b.chapters === 1 ? 'chapter' : 'chapters'}`, run: go(chapterHref(b.volume, b.book, 1)) }))
			});

		if (mode === 'all' && cmds.length) out.push({ title: 'COMMANDS', items: cmds.slice(0, 3).map(cmdItem) });

		if (res?.tags?.length)
			out.push({
				title: 'TAGS',
				items: res.tags.map((t) => ({ kind: 'tag', icon: '#', title: `#${t.name}`, meta: `${t.count} ${t.count === 1 ? 'note' : 'notes'}`, run: go(`/notes?tag=${encodeURIComponent(t.name)}`) }))
			});

		if (res?.notes?.items.length)
			out.push({
				title: `NOTES · ${res.notes.total}`,
				items: res.notes.items.map((n) => ({
					kind: 'note', icon: '¶', parts: n.parts,
					meta: [n.anchor?.label, ...n.tags.map((t) => '#' + t)].filter(Boolean).join(' · '),
					run: go(n.anchor ? refHref(n.anchor) : `/notes?q=${encodeURIComponent(text)}`)
				}))
			});

		if (res?.talks?.items.length)
			out.push({
				title: `TALKS · ${res.talks.total}`,
				items: res.talks.items.map((t) => ({
					kind: 'talk', icon: '¶', title: t.title, parts: t.parts,
					meta: [t.author, `¶${t.position}`].filter(Boolean).join(' · '),
					run: go(`/doc/${t.doc_id}#p${t.position}`)
				}))
			});

		if (res?.verses?.items.length)
			out.push({
				title: `VERSES · ${res.verses.total.toLocaleString()}`,
				items: res.verses.items.map((v) => ({ kind: 'verse', icon: '§', title: v.label, parts: v.parts, run: go(refHref(v)) }))
			});

		if (mode !== 'tags')
			out.push({
				title: '',
				items: [{ kind: 'all', icon: '/', title: `Search everything for “${text}”`, meta: 'full results', run: go(`/search?q=${encodeURIComponent(text)}`) }]
			});
		return out;
	});

	function cmdItem(c) {
		return { kind: 'command', icon: '>', title: c.title, meta: c.hint, keys: c.keys, run: c.run };
	}

	const flat = $derived(groups.flatMap((g) => g.items));
	$effect(() => {
		flat;
		if (index >= flat.length) index = 0;
	});

	function run(item) {
		closePalette();
		item?.run();
	}

	function onKey(e) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			index = flat.length ? (index + 1) % flat.length : 0;
			scrollActive();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			index = flat.length ? (index - 1 + flat.length) % flat.length : 0;
			scrollActive();
		} else if (e.key === 'Enter') {
			e.preventDefault();
			run(flat[index]);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			closePalette();
		} else if (e.key === 'Tab') {
			e.preventDefault();
			const i = FILTERS.indexOf(filter);
			filter = FILTERS[(i + (e.shiftKey ? FILTERS.length - 1 : 1)) % FILTERS.length];
			index = 0;
		}
	}

	function scrollActive() {
		tick().then(() => document.querySelector('.cp-item.active')?.scrollIntoView({ block: 'nearest' }));
	}

	// item index inside the flat list, for highlighting
	function flatIndex(gi, ii) {
		let n = 0;
		for (let g = 0; g < gi; g++) n += groups[g].items.length;
		return n + ii;
	}
</script>

{#if palette.open}
	<div class="backdrop" role="presentation" onmousedown={(e) => e.target === e.currentTarget && closePalette()}>
		<div class="dialog" role="dialog" aria-modal="true" aria-label="Command palette">
			<label class="bar">
				<span class="mono prompt" aria-hidden="true">&gt;</span>
				<span class="sr-only">Search or run a command</span>
				<input
					bind:this={input}
					bind:value={palette.query}
					onkeydown={onKey}
					placeholder="go to a verse, search, or type > for commands"
					autocomplete="off"
					spellcheck="false"
					role="combobox"
					aria-expanded="true"
					aria-controls="cp-list"
					aria-activedescendant={flat.length ? `cp-${index}` : undefined}
				/>
				{#if loading}<span class="mono spin" aria-hidden="true">…</span>{/if}
				<button class="esc mono" onclick={closePalette}>esc</button>
			</label>

			<div class="filters mono" role="tablist" aria-label="Show">
				{#each FILTERS as f}
					<button role="tab" aria-selected={mode === f} class:on={mode === f} onclick={() => ((filter = f), input?.focus())}>{f}</button>
				{/each}
				<span class="grow"></span>
				<span class="tabhint">tab ⇥</span>
			</div>

			<div class="list" id="cp-list" role="listbox">
				{#each groups as g, gi}
					{#if g.title}<div class="group mono">{g.title}</div>{/if}
					{#each g.items as item, ii}
						{@const fi = flatIndex(gi, ii)}
						<button
							id="cp-{fi}"
							class="cp-item"
							class:active={fi === index}
							role="option"
							aria-selected={fi === index}
							onmousemove={() => (index = fi)}
							onclick={() => run(item)}
						>
							<span class="icon mono k-{item.kind}" aria-hidden="true">{item.icon}</span>
							<span class="body">
								{#if item.title}<span class="title" class:mono={item.kind === 'verse' || item.kind === 'ref'}>{item.title}</span>{/if}
								{#if item.parts}<span class="snip"><Hits parts={item.parts} /></span>{/if}
								{#if item.sub}<span class="snip">{item.sub}</span>{/if}
								{#if item.meta}<span class="meta mono">{item.meta}</span>{/if}
							</span>
							{#if item.keys}<span class="keys mono">{item.keys}</span>{/if}
						</button>
					{/each}
				{/each}
				{#if text && !loading && flat.length <= 1 && mode !== 'commands'}
					<p class="none mono">no matches</p>
				{:else if mode === 'commands' && !flat.length}
					<p class="none mono">no commands match</p>
				{/if}
			</div>

			<div class="foot mono">
				<span>↑↓ move</span><span>↵ open</span><span>&gt; commands</span><span># tags</span><span>? all shortcuts</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 90;
		background: rgba(5, 7, 10, 0.7);
		display: flex;
		justify-content: center;
		align-items: flex-start;
		padding: 10vh 16px 16px;
	}
	.dialog {
		width: 660px;
		max-width: 100%;
		max-height: 76vh;
		display: flex;
		flex-direction: column;
		background: var(--bg-raised);
		border: 1px solid var(--border-strong);
		border-radius: 10px;
		box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
		overflow: hidden;
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 14px;
		height: 56px;
		border-bottom: 1px solid var(--border);
	}
	.prompt { color: var(--accent); font-size: 16px; }
	.bar input {
		flex: 1;
		min-width: 0;
		background: none;
		border: 0;
		outline: none;
		color: var(--text);
		font: 16px var(--font-mono);
	}
	.spin { color: var(--text-faint); }
	.esc {
		height: 28px;
		padding: 0 8px;
		border-radius: 4px;
		border: 1px solid var(--border-strong);
		background: none;
		color: var(--text-faint);
		font-size: 12px;
		cursor: pointer;
	}
	.filters { display: flex; gap: 4px; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 12px; }
	.filters button {
		height: 28px;
		padding: 0 10px;
		border-radius: 4px;
		border: 1px solid transparent;
		background: none;
		color: var(--text-faint);
		font: inherit;
		cursor: pointer;
	}
	.filters button.on { color: var(--accent); border-color: var(--accent-line); background: var(--accent-dim); }
	.grow { flex: 1; }
	.tabhint { color: var(--text-faint); align-self: center; }
	.list { flex: 1; overflow-y: auto; padding: 6px 8px 8px; }
	.group { font-size: 11px; letter-spacing: 0.12em; color: var(--text-faint); padding: 12px 10px 6px; }
	.cp-item {
		all: unset;
		box-sizing: border-box;
		width: 100%;
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 9px 10px;
		border-radius: 6px;
		cursor: pointer;
	}
	.cp-item.active { background: var(--surface-hover); }
	.icon { width: 18px; text-align: center; font-size: 13px; padding-top: 1px; color: var(--text-faint); }
	.k-verse, .k-ref, .k-book { color: var(--hl-doctrine); }
	.k-note { color: var(--hl-promise); }
	.k-talk { color: var(--hl-question); }
	.k-command, .k-all { color: var(--accent); }
	.k-tag { color: var(--text-muted); }
	.body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
	.title { font-size: 14px; color: var(--text); }
	.title.mono { font-size: 13px; font-weight: 600; }
	.snip {
		font-size: 13px;
		color: var(--text-muted);
		line-height: 1.45;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.meta { font-size: 11px; color: var(--text-faint); }
	.keys {
		font-size: 11px;
		color: var(--text-faint);
		border: 1px solid var(--border-strong);
		border-radius: 4px;
		padding: 1px 6px;
		white-space: nowrap;
	}
	.none { color: var(--text-faint); font-size: 12px; padding: 12px 10px; margin: 0; }
	.foot {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		padding: 10px 16px;
		border-top: 1px solid var(--border);
		font-size: 11px;
		color: var(--text-faint);
	}
	@media (max-width: 600px) {
		.backdrop { padding: 8px; }
		.dialog { max-height: 88dvh; }
		.foot { display: none; }
	}
</style>
