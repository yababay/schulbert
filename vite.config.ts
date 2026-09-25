import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
			// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
			// See https://svelte.dev/docs/kit/adapters for more information about adapters.
			adapter: adapter()
		})
	],
	server: {
			proxy: {
					// Перехватываем все запросы, которые начинаются с /api
					'/api': {
							// Замените на реальный хост вашего API-шлюза в Яндекс Облаке
							target: 'http://schulbert/', 
							changeOrigin: true,
							// Опционально: если ваш шлюз на бэкенде ожидает путь без префикса /api,
							// можно его вырезать. Но если в шлюзе путь так и прописан (/api/generate), 
							// то строчку ниже (rewrite) добавлять НЕ НАДО.
							// rewrite: (path) => path.replace(/^\/api/, '')
					}
			}
	}	
});
