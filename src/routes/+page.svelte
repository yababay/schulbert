<script lang="ts">
	import { onMount } from 'svelte';
    import Header from '$lib/components/Header.svelte';
	import { rows, query, hasComposers } from '$lib/stores/search.svelte';
    import Row from '$lib/components/Row.svelte';

	onMount(() => {
		const lastPlaylist = localStorage.getItem('lastPlaylist');
		$query = lastPlaylist || '';
	});

</script>

<Header />

<div class="container">
	<table class="table table-striped" class:d-none={$rows.length === 0}>
		<thead>
			<tr>
				<th class:d-none={!$hasComposers}>Композитор</th>
				<th>Исполнитель</th>
				<th>Альбом</th>
				<th>Трек</th>
				<th width="100" class="text-center pe-0 ps-0">Действия</th>
			</tr>
		</thead>
		<tbody>
			{#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
				<Row {composers} {artists} {album} {title} {playlist_id} {track_number} {hasComposers} />
			{/each}
		</tbody>
	</table>
</div>
