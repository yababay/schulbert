<script lang="ts">
	import { pageState, sendMpcCommand, playTrack } from '$lib/stores/player.svelte';
	import { hasComposers, query, type Track } from '$lib/stores/search.svelte';

	let { composers, artists, album, title, playlist_id, track_number }: Track = $props();
	const isCurrent = $derived(pageState.nowPlaying.includes(title));
</script>

<article class="card shadow-sm" class:border-primary={isCurrent} class:border-2={isCurrent}>
	<div class="card-body position-relative pe-5">
		<h2 class="h6 card-title mb-2">{title}</h2>
		<p class="card-text small mb-1"><span class="text-muted">Исполнитель:</span> {artists}</p>
		<p class="card-text small mb-1"><span class="text-muted">Альбом:</span> {album}</p>
		{#if $hasComposers}
			<p class="card-text small text-muted mb-0">{composers}</p>
		{/if}
		<button
			type="button"
			class="btn btn-outline-primary btn-sm rounded-circle position-absolute bottom-0 end-0 m-2"
			aria-label={`Воспроизвести: ${title}`}
			title="Воспроизвести трек"
			onclick={() => playTrack(playlist_id, track_number)}
		>
			<i class="bi bi-play-fill" aria-hidden="true"></i>
		</button>
	</div>
</article>
