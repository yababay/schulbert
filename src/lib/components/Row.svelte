<script lang="ts">
	import { sendMpcCommand, pageState, playTrack } from '$lib/stores/player.svelte';
	import { query, hasComposers } from '$lib/stores/search.svelte';

    let {
        composers,
        artists,
        album,
        title,
        playlist_id,
        track_number,
    } = $props();

    const isCurrent = $derived(pageState.nowPlaying.includes(title));

</script>

<tr class:table-primary={isCurrent}>
    <td class:d-none={!$hasComposers}>{composers}</td>
    <td>{artists}</td>
    <td>{album}</td>
    <td>{title}</td>
    <td class="d-flex align-items-center justify-content-around">
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <i class="bi bi-play-circle me-2" style="cursor: pointer;" 
            onclick={() => playTrack(playlist_id, track_number)}>
        </i>
        <i class="bi bi-pencil me-2" style="cursor: pointer;"></i>
    </td>
</tr>
