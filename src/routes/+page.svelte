<script lang="ts">
	import { onMount } from 'svelte';
	import { state, actions } from './main.svelte';
	import genresData from '$lib/assets/genres.json';
	import Brand from '$lib/components/Brand.svelte';               // 🌟 Наш новый левый компонент
	import PlayerRemote from '$lib/components/PlayerRemote.svelte';   // Наш правый компонент

	onMount(() => {
		actions.fetchPlaylists();
		actions.updateStatus();
		
		// Интервальный опрос статуса "Что играет?" раз в 5 секунд
		const interval = setInterval(() => actions.updateStatus(), 5000);
		return () => clearInterval(interval);
	});

	// Реактивные вычисления отфильтрованных плейлистов (Жанр + Оракул)
	let filteredPlaylists = $derived(
		state.playlists.filter(pl => {
			const inGenre = pl.playlist_id >= state.selectedGenre.min && pl.playlist_id <= state.selectedGenre.max;
			const matchSearch = state.searchQuery.trim() === '' || 
				pl.name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
				pl.playlist_id.toString().includes(state.searchQuery);
			return inGenre && matchSearch;
		})
	);
</script>

<div class="container-fluid bg-light text-dark min-vh-100 p-3 p-md-4">
	
	<!-- ВЕРХНЯЯ СЕРВЕРНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ (ИТОГОВЫЙ ВИД) -->
	<div class="row mb-4">
		<div class="col-12">
			<div class="card bg-white border shadow-sm rounded-3">
				<div class="card-body d-flex flex-column flex-md-row justify-content-between align-items-center gap-3 py-3">
					
					<!-- Левый бренд-компонент (Логотип + Умный статус) -->
					<Brand />

					<!-- Правый пульт управления (Кнопки + Ползунок громкости) -->
					<PlayerRemote />

				</div>
			</div>
		</div>
	</div>

	<!-- РАБОЧАЯ ЗОНА: ДВУХПАНЕЛЬНЫЙ АДАПТИВНЫЙ ИНТЕРФЕЙС -->
	<div class="row g-4">
		
		<!-- ЛЕВАЯ ПАНЕЛЬ: ИНДЕКС ПЛЕЙЛИСТОВ С РУБРИКАТОРОМ -->
		<div class="col-12 col-md-4 col-lg-3">
			<div class="card bg-white border shadow-sm rounded-3 h-100">
				<div class="card-header bg-light border-bottom py-3">
					<h6 class="mb-0 text-dark fw-bold d-flex align-items-center gap-2">
						<i class="bi bi-folder2-open text-primary"></i> Медиатека
					</h6>
				</div>
				<div class="card-body p-3">
					
					<!-- Рубрикатор Жанров -->
					<div class="mb-3">
						<label for="genreSelect" class="form-label small text-secondary fw-bold">Жанровый фильтр</label>
						<select id="genreSelect" class="form-select bg-white text-dark border py-2" bind:value={state.selectedGenre}>
							{#each genresData as genre}
								<option value={genre}>{genre.title}</option>
							{/each}
						</select>
					</div>

					<!-- Оракул-подсказчик (Autocomplete) -->
					<div class="mb-3 position-relative">
						<label for="oracleSearch" class="form-label small text-secondary fw-bold">Умный поиск (Oracle)</label>
						<div class="input-group">
							<span class="input-group-text bg-light text-muted border-end-0"><i class="bi bi-search"></i></span>
							<input 
								id="oracleSearch"
								type="text" 
								class="form-control bg-white text-dark border-start-0 py-2" 
								placeholder="Номер или имя..." 
								bind:value={state.searchQuery}
							/>
						</div>
					</div>

					<!-- Список плейлистов -->
					<div class="list-group list-group-flush border rounded bg-white overflow-auto style-scroll" style="max-height: 52vh;">
						{#if filteredPlaylists.length === 0}
							<div class="list-group-item bg-white text-muted text-center py-4">Ничего не найдено</div>
						{/if}
						{#each filteredPlaylists as pl}
							<button 
								type="button" 
								class="list-group-item list-group-item-action bg-white text-dark py-3 text-start d-flex justify-content-between align-items-center"
								class:active-playlist={state.selectedPlaylistId === pl.playlist_id}
								onclick={() => actions.fetchTracks(pl.playlist_id, pl.name)}
							>
								<span class="text-truncate me-2 fw-medium">
									<i class="bi bi-music-note-list text-muted me-1"></i> {pl.name}
								</span>
								<span class="badge bg-light text-dark border font-monospace small px-2 py-1.5">{pl.playlist_id}</span>
							</button>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- ПРАВАЯ ПАНЕЛЬ: СПИСОК ТРЕКОВ И ИХ ВЫБОР -->
		<div class="col-12 col-md-8 col-lg-9">
			<div class="card bg-white border shadow-sm rounded-3 h-100">
				<div class="card-header bg-light border-bottom py-3 d-flex justify-content-between align-items-center">
					<h6 class="mb-0 text-dark fw-bold d-flex align-items-center gap-2">
						<i class="bi bi-music-player text-primary"></i> 
						{state.selectedPlaylistId ? `Содержимое: ${state.selectedPlaylistName}` : 'Выберите плейлист в левой панели'}
					</h6>
					{#if state.selectedPlaylistId}
						<button class="btn btn-sm btn-dark fw-medium px-3 d-flex align-items-center gap-2" onclick={() => actions.sendMpcCommand({ load: state.selectedPlaylistId! })}>
							<i class="bi bi-play-circle-fill"></i> Запустить целиком
						</button>
					{/if}
				</div>
				<div class="card-body p-3">
					<div class="table-responsive border rounded bg-white style-scroll" style="max-height: 68vh;">
						<table class="table table-light table-hover mb-0 align-middle">
							<thead class="table-light border-bottom sticky-top">
								<tr>
									<th scope="col" class="text-center text-secondary py-3" style="width: 6%">#</th>
									<th scope="col" class="text-secondary py-3" style="width: 47%">Название песни</th>
									<th scope="col" class="text-secondary py-3" style="width: 47%">Исполнитель / Группа</th>
								</tr>
							</thead>
							<tbody>
								{#if state.currentTracks.length === 0}
									<tr>
										<td colspan="3" class="text-center text-muted py-5">Плейлист пуст или не выбран</td>
									</tr>
								{/if}
								{#each state.currentTracks as tr}
									<tr class="cursor-pointer" onclick={() => actions.sendMpcCommand({ load: state.selectedPlaylistId!, track: tr.track_number })}>
										<td class="font-monospace text-primary text-center fw-bold">{tr.track_number}</td>
										<td class="fw-semibold text-dark">{tr.title}</td>
										<td class="text-secondary">{tr.artist}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>

	</div>
</div>

<style>
	.cursor-pointer {
		cursor: pointer;
	}
	
	.active-playlist {
		background-color: #f8f9fa !important;
		color: #0d6efd !important;
		border-left: 4px solid #0d6efd !important;
		font-weight: 600;
	}
	.active-playlist .badge {
		background-color: #0d6efd !important;
		color: #ffffff !important;
		border-color: #0d6efd !important;
	}
	
	.style-scroll::-webkit-scrollbar {
		width: 6px;
	}
	.style-scroll::-webkit-scrollbar-track {
		background: #f1f1f1;
	}
	.style-scroll::-webkit-scrollbar-thumb {
		background: #c1c1c1;
		border-radius: 3px;
	}
	.style-scroll::-webkit-scrollbar-thumb:hover {
		background: #0d6efd;
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
