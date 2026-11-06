<script lang="ts">
	import { pageState } from '$lib/stores/player.svelte';

	let isPaused = $derived(pageState.nowPlaying.includes("[paused]"));
	let cleanTrackTitle = $derived(pageState.nowPlaying.replace(" [paused]", ""));

</script>
<p class="card-text mb-0 text-muted style-status-text d-flex align-items-center w-100 px-2 py-1 ps-1" title={cleanTrackTitle}>
    {#if pageState.isPaused}
		<i class="bi bi-disc text-secondary me-1 flex-shrink-0"></i> 
    {:else}
		<i class="bi bi-disc-fill text-primary animate-spin me-1 flex-shrink-0"></i> 
	{/if}
    <span class="text-secondary fw-medium style-status-title">&nbsp;{cleanTrackTitle}</span>
</p>

<style>
	.style-status-text {
		font-size: 0.85rem;
		min-height: 1.25rem;
		min-width: 0;
	}
	.style-status-title {
		min-width: 0;
		flex: 1 1 auto;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		-webkit-mask-image: linear-gradient(to right, #000 calc(100% - 1rem), transparent 100%);
		mask-image: linear-gradient(to right, #000 calc(100% - 1rem), transparent 100%);
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
