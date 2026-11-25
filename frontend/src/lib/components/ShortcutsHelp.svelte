<script>
	import { palette } from '#lib/commands.svelte.js';

	const sections = [
		{
			title: 'Anywhere',
			keys: [
				['⌘K  /  Ctrl K', 'command palette'],
				['/', 'command palette'],
				['g  n', 'all notes'],
				['g  p', 'plans & today\u2019s reading'],
				['g  t', 'talks & lessons'],
				['g  v', 'split view'],
				['g  g', 'study graph'],
				['g  s', 'search page'],
				['g  r', 'back to reading'],
				['?', 'this list']
			]
		},
		{
			title: 'Reading',
			keys: [
				['j  /  ↓', 'next verse'],
				['k  /  ↑', 'previous verse'],
				[']  /  [', 'next / previous chapter (or talk)'],
				['m', 'mark chapter as read'],
				['s', 'open a talk in split view'],
				['esc', 'clear selection']
			]
		},
		{
			title: 'Selected verse',
			keys: [
				['1', 'highlight: promise'],
				['2', 'highlight: Christ'],
				['3', 'highlight: doctrine'],
				['4', 'highlight: question'],
				['n', 'write a note'],
				['l', 'link to another verse'],
				['y', 'copy with reference']
			]
		},
		{
			title: 'Split view',
			keys: [
				['click', 'select a verse or paragraph'],
				['shift-click', 'select a range of verses'],
				['↵', 'link the selection']
			]
		},
		{
			title: 'Writing a note',
			keys: [
				['@', 'insert a verse  (@heb 11:1)'],
				['#', 'add a tag  (#faith)'],
				['⌘↵  /  Ctrl ↵', 'save'],
				['esc', 'cancel editing']
			]
		},
		{
			title: 'In the palette',
			keys: [
				['>', 'commands only'],
				['#', 'tags only'],
				['tab', 'switch filter'],
				['↵', 'open']
			]
		}
	];

	function close() {
		palette.help = false;
	}
</script>

{#if palette.help}
	<div class="backdrop" role="presentation" onmousedown={(e) => e.target === e.currentTarget && close()}>
		<div class="dialog" role="dialog" aria-modal="true" aria-labelledby="keys-title">
			<header>
				<h2 id="keys-title" class="mono">keyboard shortcuts</h2>
				<button class="esc mono" onclick={close}>esc</button>
			</header>
			<div class="grid">
				{#each sections as s}
					<section>
						<h3 class="mono">{s.title.toUpperCase()}</h3>
						<dl>
							{#each s.keys as [k, what]}
								<div class="row"><dt class="mono">{k}</dt><dd>{what}</dd></div>
							{/each}
						</dl>
					</section>
				{/each}
			</div>
		</div>
	</div>
{/if}

<svelte:window onkeydown={(e) => palette.help && e.key === 'Escape' && close()} />

<style>
	.backdrop {
		position: fixed; inset: 0; z-index: 95; background: rgba(5, 7, 10, 0.7);
		display: flex; justify-content: center; align-items: flex-start; padding: 8vh 16px 16px; overflow-y: auto;
	}
	.dialog {
		width: 760px; max-width: 100%; background: var(--bg-raised);
		border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
	}
	header { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--border); }
	h2 { margin: 0; font-size: 14px; font-weight: 600; color: var(--accent); }
	.esc {
		height: 28px; padding: 0 8px; border-radius: 4px; border: 1px solid var(--border-strong);
		background: none; color: var(--text-faint); font-size: 12px; cursor: pointer;
	}
	.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px 28px; padding: 18px; }
	h3 { margin: 6px 0 8px; font-size: 11px; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 500; }
	dl { margin: 0; }
	.row { display: flex; gap: 12px; padding: 5px 0; font-size: 13px; }
	dt { flex: 0 0 110px; color: var(--text); }
	dd { margin: 0; color: var(--text-muted); }
</style>
