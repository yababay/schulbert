<script lang="ts">
	import { onMount } from 'svelte';
    import Header from '$lib/components/Header.svelte';
	
	onMount(() => {
		
	});

	const rows = [
		{ id: 1, composers: 'John Lennon', album: 'Let It Be' },
		{ id: 2, composers: 'Wolfgang Amadeus Mozart', album: 'Symphony No. 40' }
	];
</script>

<div class="container">
	<Header />
	<table class="table table-striped">
		<thead>
			<tr>
				<th>ID</th>
				<th>Composers</th>
				<th>Album</th>
				<th>Actions</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as row}
				<!-- TODO: Implement actions for play and edit buttons -->
				<tr>
					<td>{row.id}</td>
					<td>{row.composers}</td>
					<td>{row.album}</td>
					<td>
						<i class="bi bi-play-circle me-2" style="cursor: pointer;"></i>
						<i class="bi bi-pencil me-2" style="cursor: pointer;"></i>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>

</style>
