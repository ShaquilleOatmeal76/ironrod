import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			// Build a single-page app: FastAPI serves index.html for every route.
			adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html' })
		})
	],
	server: {
		// During development, send API calls to the FastAPI server.
		proxy: { '/api': 'http://localhost:8000' }
	}
});
