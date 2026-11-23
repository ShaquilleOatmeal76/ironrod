<script>
	import { chapterHref } from '#lib/api.js';
	import { reader } from '#lib/reader.svelte.js';

	/** @type {{ volumes: any[] }} */
	let { volumes } = $props();

	// Which volume/book is expanded in the table of contents.
	let openVolume = $state(/** @type {string|null} */ (null));
	let openBook = $state(/** @type {string|null} */ (null));
	let filter = $state('');

	// Follow along with whatever is being read.
	$effect(() => {
		if (reader.current) {
			openVolume = reader.current.volume;
			openBook = reader.current.book;
		}
	});

	const filtered = $derived(
		filter.trim()
			? volumes
					.map((v) => ({
						...v,
						books: v.books.filter((b) =>
							b.title.toLowerCase().includes(filter.trim().toLowerCase())
						)
					}))
					.filter((v) => v.books.length)
			: volumes
	);

	function chapters(n) {
		return Array.from({ length: n }, (_, i) => i + 1);
	}

	function close() {
		reader.sidebarOpen = false;
	}
</script>

<aside class="sidebar" class:open={reader.sidebarOpen} aria-label="Library">
	<label class="filter">
		<span class="sr-only">Filter books</span>
		<span class="mono prompt" aria-hidden="true">/</span>
		<input type="search" placeholder="filter books…" bind:value={filter} />
	</label>

	<a class="volume notes-link" href="/search" onclick={close}>
		<span class="dot" aria-hidden="true"></span>
		<span class="grow">Search</span>
		<span class="mono faint">g s</span>
	</a>
	<a class="volume notes-link" href="/notes" onclick={close}>
		<span class="dot" aria-hidden="true"></span>
		<span class="grow">All Notes</span>
		<span class="mono faint">g n</span>
	</a>
	<div class="label mono lib">LIBRARY</div>
	<nav>
		{#each filtered as v (v.slug)}
			{@const vOpen = openVolume === v.slug || !!filter.trim()}
			<button
				class="volume"
				class:active={reader.current?.volume === v.slug}
				aria-expanded={vOpen}
				onclick={() => (openVolume = openVolume === v.slug ? null : v.slug)}
			>
				<span class="dot" aria-hidden="true"></span>
				<span class="grow">{v.title}</span>
				<span class="mono faint">{v.short_title}</span>
			</button>

			{#if vOpen}
				<ul class="books">
					{#each v.books as b (b.slug)}
						{@const isCurrent = reader.current?.volume === v.slug && reader.current?.book === b.slug}
						<li>
							{#if b.chapters === 1}
								<a
									class="book"
									class:current={isCurrent}
									href={chapterHref(v.slug, b.slug, 1)}
									onclick={close}>{b.title}</a
								>
							{:else}
								<button
									class="book"
									class:current={isCurrent}
									aria-expanded={openBook === b.slug}
									onclick={() => (openBook = openBook === b.slug ? null : b.slug)}
								>
									<span class="grow">{b.title}</span>
									<span class="mono faint">{b.chapters}</span>
								</button>
								{#if openBook === b.slug}
									<div class="chapters">
										{#each chapters(b.chapters) as n}
											<a
												class="mono chap"
												class:current={isCurrent && reader.current?.chapter === n}
												href={chapterHref(v.slug, b.slug, n)}
												onclick={close}>{n}</a
											>
										{/each}
									</div>
								{/if}
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		{/each}
	</nav>
</aside>

{#if reader.sidebarOpen}
	<button class="scrim" aria-label="Close library" onclick={close}></button>
{/if}

<style>
	.sidebar {
		width: 260px;
		flex: 0 0 260px;
		border-right: 1px solid var(--border);
		background: var(--bg-raised);
		overflow-y: auto;
		padding: 16px 12px 24px;
	}
	.filter {
		display: flex;
		align-items: center;
		gap: 8px;
		height: 38px;
		padding: 0 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		margin-bottom: 18px;
	}
	.filter input {
		flex: 1;
		min-width: 0;
		background: none;
		border: 0;
		outline: none;
		color: var(--text);
		font: 14px var(--font-ui);
	}
	.prompt { color: var(--accent); }
	.label {
		font-size: 11px;
		letter-spacing: 0.12em;
		color: var(--text-faint);
		padding: 0 10px 8px;
	}
	button { all: unset; box-sizing: border-box; cursor: pointer; }
	.volume {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 9px 10px;
		border-radius: var(--radius);
		font-size: 14px;
		color: var(--text-muted);
	}
	.notes-link { text-decoration: none; }
	.notes-link + .lib { margin-top: 14px; }
	.lib { padding-top: 2px; }
	.volume:hover, .book:hover { background: var(--surface-hover); }
	.volume.active { color: var(--text); }
	.dot { width: 6px; height: 6px; border-radius: 1px; background: var(--border-strong); }
	.volume.active .dot { background: var(--accent); }
	.grow { flex: 1; }
	.faint { color: var(--text-faint); font-size: 11px; }
	.books { list-style: none; margin: 2px 0 8px; padding: 0 0 0 16px; }
	.book {
		display: flex;
		align-items: center;
		width: 100%;
		padding: 7px 10px;
		border-radius: var(--radius);
		font-size: 13px;
		color: var(--text-muted);
		text-decoration: none;
	}
	.book.current { color: var(--accent); }
	.chapters {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 4px;
		padding: 6px 4px 10px 10px;
	}
	.chap {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 32px;
		border: 1px solid var(--border);
		border-radius: 4px;
		font-size: 12px;
		color: var(--text-muted);
		text-decoration: none;
	}
	.chap:hover { border-color: var(--border-strong); color: var(--text); }
	.chap.current { background: var(--accent-dim); border-color: var(--accent-line); color: var(--accent); }
	.scrim { display: none; }

	@media (max-width: 900px) {
		.sidebar {
			position: fixed;
			top: 0;
			bottom: 0;
			left: 0;
			z-index: 30;
			width: 300px;
			transform: translateX(-100%);
			transition: transform 0.2s ease;
		}
		.sidebar.open { transform: none; }
		.scrim {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 20;
			background: rgba(5, 7, 10, 0.6);
		}
	}
</style>
