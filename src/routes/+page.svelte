<script lang="ts">
    import Header from '$lib/components/Header.svelte';
	import { rows } from '$lib/stores/search.svelte';

	const handlePlayClick = (event: MouseEvent) => {
		const target = event.target as HTMLElement;
		if (target.classList.contains('bi-play-circle')) {
			const trackId = target.dataset.trackId;
			const trackNumber = target.dataset.trackNumber;
			console.log(`Play track with ID: ${trackId}, Track Number: ${trackNumber}`);
		}
	};
</script>

<div class="container">
	<Header />
	<table class="table table-striped">
		<thead>
			<tr>
				<th>№ трека</th>
				<th>Композитор</th>
				<th>Исполнитель</th>
				<th>Альбом</th>
				<th>Трек</th>
				<th>Действия</th>
			</tr>
		</thead>
		<tbody>
			{#each $rows as row (row.playlist_id + '-' + row.track_number)}
				<tr>
					<td>{row.track_number}</td>
					<td>{row.composers}</td>
					<td>{row.artists}</td>
					<td>{row.album}</td>
					<td>{row.title}</td>
					<td>
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<i class="bi bi-play-circle me-2" style="cursor: pointer;" data-track-id={row.playlist_id} data-track-number={row.track_number} onclick={handlePlayClick}></i>
						<i class="bi bi-pencil me-2" style="cursor: pointer;"></i>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>

</style>
