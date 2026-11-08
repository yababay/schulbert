<script lang="ts">
	import { sendMpcCommand, pageState, playTrack } from '$lib/stores/player.svelte';
	import { query, hasComposers } from '$lib/stores/search.svelte';
    import { currentTrack } from '$lib/stores/editor.svelte';

    let {
        composers,
        artists,
        album,
        title,
        playlist_id,
        track_number,
        showEditor
    } = $props();

    const isCurrent = $derived(pageState.nowPlaying.includes(title));

    const handleEditClick = () => {
        currentTrack.playlist_id = playlist_id;
        currentTrack.track_number = track_number;
        currentTrack.title = title || '';
        currentTrack.composers = composers || '';
        currentTrack.artists = artists || '';
        currentTrack.album = album || '';
        showEditor();
    };

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
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <i class="bi bi-pencil me-2" style="cursor: pointer;"
            onclick={handleEditClick}
        ></i>
    </td>
</tr>
