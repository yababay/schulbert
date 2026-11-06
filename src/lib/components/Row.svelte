<script lang="ts">
	import { sendMpcCommand, pageState } from '$lib/stores/player.svelte';
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
	
	const handlePlayClick = async (event: MouseEvent) => {
		const target = event.target as HTMLElement;
		if (target.classList.contains('bi-play-circle')) {
				const load = parseInt(target.dataset.playlistId || '0');
				const track = parseInt(target.dataset.trackNumber || '0');
				if (load < 1000 || track < 1) return;
                // console.log('load:', load, 'track:', track);
				await sendMpcCommand({ action: 'load', load, track});
				query.set(`${load}`)
                localStorage.setItem('lastPlaylist', `${load}`);
		}
	}

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
            data-playlist-id={playlist_id} data-track-number={track_number} 
            onclick={handlePlayClick}>
        </i>
        <i class="bi bi-pencil me-2" style="cursor: pointer;"></i>
    </td>
</tr>
