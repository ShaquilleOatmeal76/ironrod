<script>
	// Renders a search snippet with the matched words emphasized.
	// The server sends [{text, hit}] pieces instead of HTML, so nothing here
	// can ever inject markup.
	/** @type {{ parts: {text: string, hit: boolean}[] }} */
	let { parts } = $props();
</script>

{#each parts as p}{#if p.hit}<mark>{p.text}</mark>{:else}{p.text}{/if}{/each}

<style>
	mark {
		background: color-mix(in srgb, var(--accent) 18%, transparent);
		color: var(--text);
		border-radius: 2px;
		padding: 0 1px;
	}
</style>
