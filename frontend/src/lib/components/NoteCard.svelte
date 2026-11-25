<script>
	import { goto } from '$app/navigation';
	import { api, refHref, paraHref } from '#lib/api.js';
	import NoteEditor from './NoteEditor.svelte';

	/** @type {{ note: any, showAnchor?: boolean, onchanged?: () => void }} */
	let { note, showAnchor = false, onchanged } = $props();

	let editing = $state(false);
	let confirmDelete = $state(false);

	function when(ts) {
		// SQLite stores UTC as "YYYY-MM-DD HH:MM:SS"
		const d = new Date(ts.replace(' ', 'T') + 'Z');
		/** @type {Intl.DateTimeFormatOptions} */
		const opts = d.getFullYear() === new Date().getFullYear()
			? { month: 'short', day: 'numeric' }
			: { month: 'short', day: 'numeric', year: 'numeric' };
		return d.toLocaleDateString(undefined, opts).toLowerCase();
	}

	// Clicking an @reference chip opens that verse.
	async function onBodyClick(e) {
		const chip = /** @type {HTMLElement} */ (e.target).closest('[data-type="verseRef"]');
		if (!chip) return;
		try {
			const r = await api.resolveRef(chip.getAttribute('data-label') ?? '');
			goto(refHref(r));
		} catch {
			/* unknown reference */
		}
	}

	async function save(html) {
		await api.updateNote(note.id, html);
		editing = false;
		onchanged?.();
	}

	async function remove() {
		if (!confirmDelete) {
			confirmDelete = true;
			setTimeout(() => (confirmDelete = false), 3000);
			return;
		}
		await api.deleteNote(note.id);
		onchanged?.();
	}
</script>

<article class="card">
	<header>
		<span class="who mono">you</span>
		<span class="meta mono">· {when(note.updated_at)}</span>
		{#if note.relation === 'mentions' && note.anchor}
			<span class="meta mono">· mentioned in a note on</span>
		{/if}
		{#if (showAnchor || note.relation === 'mentions') && note.anchor}
			<a class="anchor mono" href={refHref(note.anchor)}>{note.anchor.label}</a>
		{:else if showAnchor && note.para}
			<a class="anchor mono talk" href={paraHref(note.para)}>{note.para.doc_title} ¶{note.para.position}</a>
		{/if}
		<span class="grow"></span>
		{#if !editing && note.relation !== 'mentions'}
			<button class="mini" onclick={() => (editing = true)}>edit</button>
			<button class="mini" class:danger={confirmDelete} onclick={remove}>{confirmDelete ? 'sure?' : 'delete'}</button>
		{/if}
	</header>

	{#if editing}
		<NoteEditor html={note.html} saveLabel="Update" autofocus onsave={save} oncancel={() => (editing = false)} />
	{:else}
		<!-- note.html was sanitized by the server (allowlist), so it is safe to render -->
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<div class="note-body" onclick={onBodyClick}>{@html note.html}</div>
		{#if note.tags.length}
			<div class="tags">
				{#each note.tags as t}<a class="tag mono" href="/notes?tag={encodeURIComponent(t)}">#{t}</a>{/each}
			</div>
		{/if}
	{/if}
</article>

<style>
	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 14px 16px;
	}
	header {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin-bottom: 8px;
	}
	.who { font-size: 12px; font-weight: 600; color: var(--accent); }
	.meta { font-size: 11px; color: var(--text-faint); }
	.anchor { font-size: 12px; color: var(--hl-doctrine); text-decoration: none; }
	.anchor:hover { text-decoration: underline; }
	.anchor.talk { color: var(--hl-question); }
	.grow { flex: 1; }
	.mini {
		border: 0;
		background: none;
		color: var(--text-faint);
		font: 11px var(--font-mono);
		padding: 4px 6px;
		border-radius: 4px;
		cursor: pointer;
	}
	.mini:hover { color: var(--text); background: var(--surface-hover); }
	.mini.danger { color: var(--hl-promise); }
	.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
	.tag {
		font-size: 11px;
		color: var(--text-muted);
		background: #1a2029;
		border-radius: 4px;
		padding: 3px 8px;
		text-decoration: none;
	}
	.tag:hover { color: var(--text); }
</style>
