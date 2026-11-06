<script lang="ts">
	import { onMount } from 'svelte';
    import {rows, query, hasComposers} from '$lib/stores/search.svelte';
    import Row from '$lib/components/Row.svelte';
    import Card from '$lib/components/Card.svelte';

	onMount(() => {
		const lastPlaylist = localStorage.getItem('lastPlaylist');
		$query = lastPlaylist || '';
	});

</script>

{#if $rows.length > 0}
    <div class="d-flex d-md-none flex-column gap-2">
        {#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
            <Card {composers} {artists} {album} {title} {playlist_id} {track_number} />
        {/each}
    </div>
    <table class="table table-striped d-none d-md-table">
        <thead>
            <tr>
                <th class:d-none={!$hasComposers}>Композитор</th>
                <th>Исполнитель</th>
                <th>Альбом</th>
                <th>Трек</th>
                <th style="width: 100px" class="text-center pe-0 ps-0">Действия</th>
            </tr>
        </thead>
        <tbody>
            {#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
                <Row {composers} {artists} {album} {title} {playlist_id} {track_number} />
            {/each}
        </tbody>
    </table>
{/if}
