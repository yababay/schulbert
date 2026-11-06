<script lang="ts">
    import { pageState, sendMpcCommand } from '$lib/stores/player.svelte';
</script>

<!-- Bootstrap Range ползунок громкости -->
<div class="d-flex align-items-center gap-2 border rounded px-3 py-1 bg-light shadow-sm w-100"
     title={`Громкость: ${pageState.volume}%`}
>
    {#if pageState.volume === 0}
        <i class="bi bi-volume-mute-fill text-muted fs-5"></i>
    {:else if pageState.volume < 50}
        <i class="bi bi-volume-down-fill text-secondary fs-5"></i>
    {:else}
        <i class="bi bi-volume-up-fill text-dark fs-5"></i>
    {/if}
    
    <input 
        type="range" 
        class="form-range" 
        id="volumeRange" 
        min="0" 
        max="100" 
        step="5" 
        bind:value={pageState.volume} 
        onchange={(e) => sendMpcCommand({ action: 'volume', volume: (e.target as HTMLInputElement).value })}
        title={`Громкость: ${pageState.volume}%`}
    />
    <span class="small font-monospace text-secondary style-percent">{pageState.volume}%</span>
</div>

<style>
	.style-percent {
		min-width: 38px;
		text-align: right;
	}
</style>
