<script>
	import { onMount, onDestroy, untrack } from 'svelte';
	import { Editor } from '@tiptap/core';
	import { noteExtensions } from '#lib/editor/extensions.js';

	/**
	 * @type {{
	 *   html?: string, placeholder?: string, saveLabel?: string, footer?: string,
	 *   autofocus?: boolean, focusSignal?: number,
	 *   onsave: (html: string) => Promise<void> | void, oncancel?: () => void
	 * }}
	 */
	let {
		html = '',
		placeholder = 'Write a note… @ links a verse, # adds a tag',
		saveLabel = 'Save',
		footer = '',
		autofocus = false,
		focusSignal = 0,
		onsave,
		oncancel
	} = $props();

	let el = $state();
	/** @type {Editor | null} */
	let editor = $state(null);
	let empty = $state(true);
	let saving = $state(false);
	let error = $state('');
	// bumped on every editor transaction so toolbar "active" states refresh
	let tick = $state(0);

	onMount(() => {
		editor = new Editor({
			element: el,
			extensions: noteExtensions(placeholder),
			content: html,
			autofocus: autofocus ? 'end' : false,
			editorProps: {
				attributes: { class: 'note-body editor', 'aria-label': 'Note', role: 'textbox', 'aria-multiline': 'true' },
				handleKeyDown: (_view, e) => {
					if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
						save();
						return true;
					}
					if (e.key === 'Escape' && oncancel) {
						oncancel();
						return true;
					}
					return false;
				}
			},
			onTransaction: () => {
				empty = editor?.isEmpty ?? true;
				tick++;
			}
		});
		empty = editor.isEmpty;
	});

	onDestroy(() => editor?.destroy());

	// The parent can ask us to take focus (e.g. pressing "n" in the reader).
	let lastSignal = untrack(() => focusSignal);
	$effect(() => {
		if (focusSignal !== lastSignal) {
			lastSignal = focusSignal;
			editor?.commands.focus('end');
		}
	});

	async function save() {
		if (!editor || editor.isEmpty || saving) return;
		saving = true;
		error = '';
		try {
			await onsave(editor.getHTML());
			if (!html) editor.commands.clearContent(true);
		} catch (e) {
			error = e.message || 'Could not save';
		} finally {
			saving = false;
		}
	}

	function is(name, attrs = undefined) {
		tick; // re-run when the editor changes
		return editor?.isActive(name, attrs) ?? false;
	}

	const tools = [
		{ label: 'Bold', text: 'B', cls: 'b', run: () => editor.chain().focus().toggleBold().run(), active: () => is('bold') },
		{ label: 'Italic', text: 'I', cls: 'i', run: () => editor.chain().focus().toggleItalic().run(), active: () => is('italic') },
		{ label: 'Heading', text: 'H', cls: 'h', run: () => editor.chain().focus().toggleHeading({ level: 3 }).run(), active: () => is('heading') },
		{ label: 'Bulleted list', text: '•', cls: '', run: () => editor.chain().focus().toggleBulletList().run(), active: () => is('bulletList') },
		{ label: 'Quote', text: '❝', cls: '', run: () => editor.chain().focus().toggleBlockquote().run(), active: () => is('blockquote') }
	];

	function insertTrigger(ch) {
		editor?.chain().focus().insertContent(` ${ch}`).run();
	}
</script>

<div class="composer">
	<div class="toolbar" role="toolbar" aria-label="Formatting">
		{#each tools as t}
			<button type="button" class="tool {t.cls}" class:on={t.active()} aria-label={t.label} aria-pressed={t.active()} onclick={t.run}>{t.text}</button>
		{/each}
		<span class="sep" aria-hidden="true"></span>
		<button type="button" class="tool mono accent" aria-label="Insert verse reference" onclick={() => insertTrigger('@')}>@ref</button>
		<button type="button" class="tool mono" aria-label="Insert tag" onclick={() => insertTrigger('#')}>#tag</button>
	</div>

	<div bind:this={el} class="area"></div>

	{#if error}<p class="error" role="alert">{error}</p>{/if}

	<div class="actions">
		<span class="mono foot">{footer}</span>
		{#if oncancel}
			<button type="button" class="ghost" onclick={oncancel}>Cancel</button>
		{/if}
		<button type="button" class="save" disabled={empty || saving} onclick={save}>
			{saving ? 'Saving…' : saveLabel} <span class="mono kbd">⌘↵</span>
		</button>
	</div>
</div>

<style>
	.composer {
		background: var(--surface);
		border: 1px solid var(--border-strong);
		border-radius: 8px;
	}
	.composer:focus-within { border-color: var(--accent-line); }
	.toolbar {
		display: flex;
		flex-wrap: wrap;
		gap: 2px;
		padding: 6px;
		border-bottom: 1px solid var(--border);
	}
	.tool {
		min-width: 32px;
		height: 32px;
		padding: 0 8px;
		border: 0;
		border-radius: 4px;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		font-size: 14px;
	}
	.tool:hover { background: var(--surface-hover); color: var(--text); }
	.tool.on { background: var(--accent-dim); color: var(--accent); }
	.tool.b { font-weight: 700; }
	.tool.i { font-style: italic; font-family: var(--font-scripture); }
	.tool.h { font-weight: 600; }
	.tool.mono { font-family: var(--font-mono); font-size: 13px; }
	.tool.accent { color: var(--accent); }
	.sep { width: 1px; background: var(--border-strong); margin: 6px 4px; }
	.area { padding: 2px 0; }
	.area :global(.editor) {
		min-height: 84px;
		max-height: 320px;
		overflow-y: auto;
		padding: 10px 14px;
		outline: none;
	}
	.area :global(.editor p.is-editor-empty:first-child::before) {
		content: attr(data-placeholder);
		color: var(--text-faint);
		float: left;
		height: 0;
		pointer-events: none;
	}
	.actions {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 8px 8px 14px;
	}
	.foot { flex: 1; font-size: 11px; color: var(--text-faint); }
	.save, .ghost {
		height: 34px;
		padding: 0 14px;
		border-radius: var(--radius);
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.save { border: 0; background: var(--accent); color: var(--accent-ink); }
	.save:disabled { opacity: 0.4; cursor: default; }
	.ghost { border: 1px solid var(--border-strong); background: transparent; color: var(--text-muted); }
	.kbd { font-weight: 500; opacity: 0.8; }
	.error { margin: 0 14px 8px; color: var(--hl-promise); font-size: 13px; }
</style>
