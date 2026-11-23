<script>
	import { untrack } from 'svelte';
	import { api, refHref } from '#lib/api.js';
	import { byId } from '#lib/highlights.js';
	import NoteCard from './NoteCard.svelte';
	import NoteEditor from './NoteEditor.svelte';

	/**
	 * @type {{
	 *   verseId: number, noteSignal?: number, linkSignal?: number,
	 *   onchanged?: () => void, onclose?: () => void
	 * }}
	 */
	let { verseId, noteSignal = 0, linkSignal = 0, onchanged, onclose } = $props();

	let details = $state(/** @type {any} */ (null));
	let tab = $state(/** @type {'notes'|'links'} */ ('notes'));
	let error = $state('');
	let reloadKey = $state(0);

	$effect(() => {
		const id = verseId;
		reloadKey;
		error = '';
		api.verse(id).then(
			(d) => {
				if (id === verseId) details = d;
			},
			(e) => (error = e.message)
		);
	});

	function changed() {
		reloadKey++;
		onchanged?.();
	}

	// "n" in the reader -> show notes tab and focus the composer.
	let composerFocus = $state(0);
	let lastNote = untrack(() => noteSignal);
	$effect(() => {
		if (noteSignal !== lastNote) {
			lastNote = noteSignal;
			tab = 'notes';
			composerFocus++;
		}
	});

	// "l" in the reader -> show links tab and focus the reference box.
	let linkInput = $state();
	let lastLink = untrack(() => linkSignal);
	$effect(() => {
		if (linkSignal !== lastLink) {
			lastLink = linkSignal;
			tab = 'links';
			queueMicrotask(() => linkInput?.focus());
		}
	});

	async function addNote(html) {
		await api.createNote(html, verseId, verseId);
		changed();
	}

	// --- links ---
	let labels = $state(['related']);
	api.linkLabels().then((l) => (labels = l), () => {});
	let target = $state('');
	let label = $state('related');
	let preview = $state(/** @type {any} */ (null));
	let linkError = $state('');
	let timer;

	function onTargetInput() {
		linkError = '';
		clearTimeout(timer);
		const q = target;
		if (!q.trim()) {
			preview = null;
			return;
		}
		timer = setTimeout(async () => {
			try {
				const r = await api.resolveRef(q);
				if (q === target) preview = r;
			} catch {
				if (q === target) preview = null;
			}
		}, 200);
	}

	async function addLink(e) {
		e.preventDefault();
		linkError = '';
		try {
			await api.createLink(verseId, verseId, target, label);
			target = '';
			preview = null;
			changed();
		} catch (err) {
			linkError = err.message;
		}
	}

	async function removeLink(id) {
		await api.deleteLink(id);
		changed();
	}

	const noteCount = $derived(details?.notes.length ?? 0);
	const linkCount = $derived(details?.links.length ?? 0);
</script>

<section class="panel" aria-label="Verse details">
	<header class="head">
		<div class="title-row">
			<h2 class="mono">{details?.ref.label ?? '…'}</h2>
			{#if details?.highlight}
				<span class="hl mono" style="--c:{byId[details.highlight].color}">
					<span class="sw" aria-hidden="true"></span>{byId[details.highlight].label.toLowerCase()}
				</span>
			{/if}
			<span class="grow"></span>
			{#if onclose}
				<button class="close" aria-label="Close panel" onclick={onclose}>×</button>
			{/if}
		</div>
		<div class="tabs" role="tablist" aria-label="Panel views">
			<button role="tab" aria-selected={tab === 'notes'} class:on={tab === 'notes'} onclick={() => (tab = 'notes')}>
				Notes <span class="mono n">{noteCount}</span>
			</button>
			<button role="tab" aria-selected={tab === 'links'} class:on={tab === 'links'} onclick={() => (tab = 'links')}>
				Links <span class="mono n">{linkCount}</span>
			</button>
		</div>
	</header>

	<div class="scroll">
		{#if error}
			<p class="muted">Couldn't load this verse: {error}</p>
		{:else if !details}
			<p class="muted mono">loading…</p>
		{:else if tab === 'notes'}
			{#if noteCount === 0}
				<p class="muted">No notes on this verse yet. Start one below.</p>
			{/if}
			{#each details.notes as note (note.id)}
				<NoteCard {note} onchanged={changed} />
			{/each}
		{:else}
			<form class="addlink" onsubmit={addLink}>
				<label class="field">
					<span class="sr-only">Link to reference</span>
					<span class="mono prompt" aria-hidden="true">→</span>
					<input
						bind:this={linkInput}
						bind:value={target}
						oninput={onTargetInput}
						placeholder="link to… e.g. ether 12:6"
						autocomplete="off"
					/>
				</label>
				<div class="row">
					<label class="sel">
						<span class="sr-only">Relationship</span>
						<select bind:value={label}>
							{#each labels as l}<option value={l}>{l}</option>{/each}
						</select>
					</label>
					<button class="add" disabled={!preview}>+ Link</button>
				</div>
				{#if preview}
					<p class="preview"><span class="mono">{preview.label}</span> — {preview.text}</p>
				{:else if target.trim()}
					<p class="muted mono small">keep typing… (book chapter:verse)</p>
				{/if}
				{#if linkError}<p class="err" role="alert">{linkError}</p>{/if}
			</form>

			{#each details.links as l (l.id)}
				<div class="link">
					<div class="link-top">
						<a class="mono ref" href={refHref(l.other)}>{l.other.label}</a>
						<span class="grow"></span>
						<button class="mini" aria-label="Remove link to {l.other.label}" onclick={() => removeLink(l.id)}>remove</button>
					</div>
					<a class="snippet" href={refHref(l.other)}>{l.other.text}</a>
					<div class="mono why">↳ {l.label}</div>
				</div>
			{/each}
			{#if linkCount === 0}
				<p class="muted">Nothing linked yet. Type a reference above.</p>
			{/if}
		{/if}
	</div>

	{#if tab === 'notes'}
		<div class="composer-wrap">
			<NoteEditor onsave={addNote} focusSignal={composerFocus} saveLabel="Save note" footer="visible: household" />
		</div>
	{/if}
</section>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		background: var(--bg-raised);
	}
	.head { padding: 16px 20px 0; }
	.title-row { display: flex; align-items: center; gap: 10px; }
	h2 { margin: 0; font-size: 17px; font-weight: 600; }
	.hl {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		color: var(--text-muted);
		border: 1px solid var(--border-strong);
		border-radius: 4px;
		padding: 2px 8px;
	}
	.sw { width: 10px; height: 10px; border-radius: 2px; background: var(--c); }
	.grow { flex: 1; }
	.close {
		width: 40px;
		height: 40px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: transparent;
		color: var(--text-muted);
		font-size: 20px;
		cursor: pointer;
	}
	@media (min-width: 1101px) { .close { display: none; } }
	.tabs { display: flex; gap: 4px; margin-top: 12px; border-bottom: 1px solid var(--border); }
	.tabs button {
		all: unset;
		cursor: pointer;
		padding: 10px 12px 9px;
		font-size: 14px;
		font-weight: 500;
		color: var(--text-faint);
		border-bottom: 2px solid transparent;
	}
	.tabs button.on { color: var(--text); border-bottom-color: var(--accent); }
	.tabs button:focus-visible { outline: 2px solid var(--accent); }
	.n { font-size: 11px; color: var(--text-faint); }
	.scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 16px 20px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.muted { margin: 0; color: var(--text-faint); font-size: 14px; }
	.small { font-size: 12px; }
	.composer-wrap { padding: 12px 20px 16px; border-top: 1px solid var(--border); }

	.addlink { display: flex; flex-direction: column; gap: 8px; padding-bottom: 6px; }
	.field {
		display: flex;
		align-items: center;
		gap: 8px;
		height: 42px;
		padding: 0 12px;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius);
		background: var(--surface);
	}
	.field:focus-within { border-color: var(--accent-line); }
	.field input {
		flex: 1;
		min-width: 0;
		background: none;
		border: 0;
		outline: none;
		color: var(--text);
		font: 14px var(--font-mono);
	}
	.prompt { color: var(--accent); }
	.row { display: flex; gap: 8px; }
	.sel { flex: 1; }
	select {
		width: 100%;
		height: 38px;
		background: var(--surface);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius);
		color: var(--text);
		font: 13px var(--font-mono);
		padding: 0 8px;
	}
	.add {
		height: 38px;
		padding: 0 14px;
		border-radius: var(--radius);
		border: 1px solid var(--accent-line);
		background: var(--accent-dim);
		color: var(--accent);
		font-weight: 600;
		cursor: pointer;
	}
	.add:disabled { opacity: 0.4; cursor: default; }
	.preview { margin: 0; font-size: 13px; color: var(--text-muted); line-height: 1.5; }
	.preview .mono { color: var(--accent); }
	.err { margin: 0; color: var(--hl-promise); font-size: 13px; }

	.link {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 12px 14px;
	}
	.link-top { display: flex; align-items: center; }
	.ref { font-size: 13px; font-weight: 600; color: var(--hl-doctrine); text-decoration: none; }
	.snippet {
		display: block;
		margin-top: 4px;
		font-size: 13px;
		line-height: 1.55;
		color: var(--text-muted);
		text-decoration: none;
	}
	.why { margin-top: 6px; font-size: 11px; color: var(--text-faint); }
	.mini {
		border: 0;
		background: none;
		color: var(--text-faint);
		font: 11px var(--font-mono);
		padding: 4px 6px;
		border-radius: 4px;
		cursor: pointer;
	}
	.mini:hover { color: var(--hl-promise); background: var(--surface-hover); }
</style>
