<script lang="ts">
	import favicon from '$lib/assets/ai-music.svg';
	import { PUBLIC_PAGE_TITLE } from '$env/static/public';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{PUBLIC_PAGE_TITLE}</title>
</svelte:head>

<main>
{@render children()}
</main>

<style>
	main {
		display: block;
		box-sizing: border-box;
		min-height: 100vh;
		padding: 0;
		margin: 0;
		background: #f8f9fa; /* Сменили на светлый системный фон Bootstrap */
	}
</style>


