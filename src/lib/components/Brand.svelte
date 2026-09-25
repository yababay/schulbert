<script lang="ts">
	import { pageState } from '../../routes/main.svelte';
	import logoImg from '$lib/assets/schulbert.svg';

	const LOGO_WIDTH = "280"; 
	const LOGO_HEIGHT = "60";

	let isStopped = $derived(
		pageState.nowPlaying.includes("Воспроизведение остановлено") || 
		pageState.nowPlaying.trim() === "" || 
		pageState.nowPlaying.includes("Тишина")
	);
	
	let isPaused = $derived(pageState.nowPlaying.includes("[paused]"));
	let isPlaying = $derived(!isStopped && !isPaused);
	let cleanTrackTitle = $derived(pageState.nowPlaying.replace(" [paused]", ""));
</script>

<div class="d-flex flex-column align-items-center align-items-md-start select-none">
	<img src={logoImg} alt="Schubert Logo" width={LOGO_WIDTH} height={LOGO_HEIGHT} class="img-fluid mb-2" />
	
	<p class="card-text mb-0 text-muted style-status-text">
		{#if isPlaying}
			<i class="bi bi-disc-fill text-primary animate-spin me-1"></i> 
			<span class="fw-semibold text-secondary">Сейчас играет:</span> {cleanTrackTitle}
		{:else if isPaused}
			<i class="bi bi-disc text-secondary me-1"></i> 
			<span class="fw-semibold text-secondary">Пауза:</span> {cleanTrackTitle}
		{:else}
			<i class="bi bi-music-note text-muted me-1"></i> 
			<span class="text-secondary fw-medium">Музыкальный ассистент «Шульберта»</span>
		{/if}
	</p>
</div>

<style>
	.style-status-text {
		font-size: 0.85rem;
		min-height: 1.25rem;
	}
	.select-none {
		user-select: none;
	}
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	:global(.animate-spin) {
		display: inline-block;
		animation: spin 4s linear infinite;
	}
</style>
