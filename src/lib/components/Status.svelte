<script lang="ts">
	import { pageState } from '$lib/stores/player.svelte';

	let isStopped = $derived(
		pageState.nowPlaying.includes("Воспроизведение остановлено") || 
		pageState.nowPlaying.trim() === "" || 
		pageState.nowPlaying.includes("Тишина")
	);
	
	let isPaused = $derived(pageState.nowPlaying.includes("[paused]"));
	let isPlaying = $derived(!isStopped && !isPaused);
	let cleanTrackTitle = $derived(pageState.nowPlaying.replace(" [paused]", ""));
</script>
<p class="card-text mb-0 text-muted style-status-text w-75 text-truncate d-flex align-items-center p-5">
    {#if isPlaying}
        <i class="bi bi-disc-fill text-primary animate-spin me-1"></i> 
        <!-- span class="fw-semibold text-secondary">Сейчас играет:</span -->&nbsp;{cleanTrackTitle}
    {:else if isPaused}
        <i class="bi bi-disc text-secondary me-1"></i> 
        <!-- span class="fw-semibold text-secondary">Пауза:</span -->&nbsp;{cleanTrackTitle}
    {:else}
        <i class="bi bi-music-note text-muted me-1"></i> 
        <span class="text-secondary fw-medium">Музыкальный ассистент «Шульберт»</span>
    {/if}
</p>

<style>
	.style-status-text {
		font-size: 0.85rem;
		min-height: 1.25rem;
		text-overflow: ellipsis;
		overflow: hidden;
		white-space: nowrap;
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
