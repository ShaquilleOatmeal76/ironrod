<script>
	import { suggest, choose } from '#lib/editor/suggest.svelte.js';

	// Keep the popup on screen: below the cursor, or above it near the bottom.
	const style = $derived.by(() => {
		const r = suggest.rect;
		if (!r) return 'display:none';
		const width = 320;
		const left = Math.max(8, Math.min(r.left, window.innerWidth - width - 8));
		const below = r.bottom + 6;
		const flip = below + 280 > window.innerHeight;
		return flip
			? `left:${left}px; bottom:${window.innerHeight - r.top + 6}px; width:${width}px`
			: `left:${left}px; top:${below}px; width:${width}px`;
	});
</script>

{#if suggest.open}
	<div class="pop" {style} role="listbox" aria-label={suggest.kind === 'ref' ? 'Scripture references' : 'Tags'}>
		{#if suggest.items.length === 0}
			<div class="empty mono">{suggest.kind === 'ref' ? 'no match — try "alma 32:21"' : 'type a tag name'}</div>
		{/if}
		{#each suggest.items as item, i}
			{#if item.type === 'hint'}
				<div class="empty mono">type a reference — e.g. alma 32:21</div>
			{:else}
				<button
					type="button"
					role="option"
					aria-selected={i === suggest.index}
					class:active={i === suggest.index}
					onmousedown={(e) => {
						e.preventDefault();
						choose(i);
					}}
					onmouseenter={() => (suggest.index = i)}
				>
					{#if item.type === 'ref'}
						<span class="title mono">§ {item.label}</span>
						<span class="sub">{item.text}</span>
					{:else if item.type === 'book'}
						<span class="title"><span class="mono icon">§</span>{item.title}</span>
						<span class="sub mono">{item.chapters} {item.chapters === 1 ? 'chapter' : 'chapters'} · ↵ to continue</span>
					{:else if item.type === 'tag'}
						<span class="title mono">#{item.name}</span>
						<span class="sub mono">{item.count} {item.count === 1 ? 'note' : 'notes'}</span>
					{:else if item.type === 'new'}
						<span class="title mono">#{item.name}</span>
						<span class="sub mono">new tag</span>
					{/if}
				</button>
			{/if}
		{/each}
	</div>
{/if}

<style>
	.pop {
		position: fixed;
		z-index: 100;
		max-height: 280px;
		overflow-y: auto;
		padding: 6px;
		background: var(--bg-raised);
		border: 1px solid var(--border-strong);
		border-radius: 8px;
		box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55);
	}
	button {
		all: unset;
		box-sizing: border-box;
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		padding: 8px 10px;
		border-radius: 5px;
		cursor: pointer;
	}
	button.active { background: var(--surface-hover); }
	.title { font-size: 13px; color: var(--text); font-weight: 600; }
	.icon { color: var(--hl-doctrine); margin-right: 6px; }
	.sub {
		font-size: 12px;
		color: var(--text-faint);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.empty { padding: 8px 10px; font-size: 12px; color: var(--text-faint); }
</style>
