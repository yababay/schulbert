<script lang="ts">
    import Header from '$lib/components/Header.svelte';
	import { rows } from '$lib/stores/search.svelte';
    import Row from '$lib/components/Row.svelte';
</script>

<Header />

<div class="container">
	<table class="table table-striped" class:d-none={$rows.length === 0}>
		<thead>
			<tr>
				<th>Композитор</th>
				<th>Исполнитель</th>
				<th>Альбом</th>
				<th>Трек</th>
				<th>Действия</th>
			</tr>
		</thead>
		<tbody>
			{#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
				<Row {composers} {artists} {album} {title} {playlist_id} {track_number} />
			{/each}
		</tbody>
	</table>
</div>
