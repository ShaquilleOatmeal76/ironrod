<script>
	import { page } from '$app/state';
</script>

<div class="err">
	<p class="mono code">{page.status}</p>
	<h1>{page.error?.message ?? 'Something went wrong'}</h1>
	<a href="/">Back to reading</a>
</div>

<style>
	.err { max-width: 520px; margin: 80px auto; padding: 0 24px; text-align: center; }
	.code { color: var(--accent); font-size: 14px; letter-spacing: 0.1em; }
	h1 { font-family: var(--font-scripture); font-weight: 600; }
</style>
