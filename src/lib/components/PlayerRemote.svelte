<script lang="ts">
	import { state as pageState, actions } from '../../routes/main.svelte';

	// Реактивно вычисляем состояние Полного Стопа на основе строки статуса Cubi
	let isStopped = $derived(
		pageState.nowPlaying.includes("Воспроизведение остановлено") || 
		pageState.nowPlaying.trim() === "" ||
		pageState.nowPlaying.includes("Тишина")
	);
	
	// Локальный флаг состояния для плавного переключения иконок play/pause
	let localIsPlaying = $state(false);
	
	// Синхронизируем локальный флаг с ответами сервера Cubi
	$effect(() => {
		if (isStopped) {
			localIsPlaying = false;
		} else if (pageState.nowPlaying && !isStopped) {
			if (pageState.nowPlaying.includes("[paused]")) {
				localIsPlaying = false;
			} else {
				localIsPlaying = true;
			}
		}
	});

	// Умный тогл Play/Pause
	function handlePlayPauseToggle() {
		if (localIsPlaying) {
			actions.sendMpcCommand({ action: 'pause' });
			localIsPlaying = false;
		} else {
			actions.sendMpcCommand({ action: 'play' });
			localIsPlaying = true;
		}
	}

	// Жесткий стоп плеера
	function handleStop() {
		actions.sendMpcCommand({ action: 'stop' }); // На сервере mpc clear
		localIsPlaying = false;
		pageState.nowPlaying = "Воспроизведение остановлено или очередь пуста.";
	}
</script>

<!-- ОБЪЕДИНЕННАЯ ПРАВАЯ ПАНЕЛЬ С УМНОЙ СЕМАНТИКОЙ КНОПОК -->
<div class="d-flex flex-column flex-sm-row align-items-center gap-3 backend-remote-panel">
	
	<!-- Группа управления треками (динамическая видимость) -->
	<div class="btn-group shadow-sm" role="group">
		
		<!-- Динамическая кнопка Play/Pause (Доступна всегда) -->
		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title={localIsPlaying ? "Поставить на паузу" : "Запустить воспроизведение"}
			onclick={handlePlayPauseToggle}
		>
			{#if localIsPlaying}
				<i class="bi bi-pause-fill fs-5"></i>
			{:else}
				<i class="bi bi-play-fill fs-5"></i>
			{/if}
		</button>

		<!-- 🌟 СЕМАНТИЧЕСКИЙ ФИЛЬТР: Кнопка Стоп появляется ТОЛЬКО если трек играет или на паузе -->
		{#if !isStopped}
			<button 
				type="button" 
				class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
				title="Остановить воспроизведение и сбросить очередь"
				onclick={handleStop}
			>
				<i class="bi bi-stop-fill fs-5"></i>
			</button>
		{/if}

		<!-- Кнопка Следующий трек (Доступна всегда для пролистывания) -->
		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title="Перейти к следующему треку"
			onclick={() => actions.sendMpcCommand({ action: 'next' })}
		>
			<i class="bi bi-skip-forward-fill fs-5"></i>
		</button>
	</div>

	<!-- Легковесный Bootstrap Range ползунок громкости с шагом 5% -->
	<div class="d-flex align-items-center gap-2 border rounded px-3 py-1.5 bg-light shadow-sm" style="min-width: 180px;">
		{#if pageState.volume === 0}
			<i class="bi bi-volume-mute-fill text-muted fs-5" title="Звук выключен"></i>
		{:else if pageState.volume < 50}
			<i class="bi bi-volume-down-fill text-secondary fs-5" title="Тихая громкость"></i>
		{:else}
			<i class="bi bi-volume-up-fill text-dark fs-5" title="Высокая громкость"></i>
		{/if}
		
		<input 
			type="range" 
			class="form-range" 
			id="volumeRange" 
			min="0" 
			max="100" 
			step="5" 
			bind:value={pageState.volume} 
			onchange={(e) => actions.sendMpcCommand({ volume: (e.target as HTMLInputElement).value })}
			title={`Громкость: ${pageState.volume}%`}
		/>
		<span class="small font-monospace text-secondary style-percent">{pageState.volume}%</span>
	</div>

</div>

<style>
	@media (max-width: 576px) {
		.backend-remote-panel {
			width: 100%;
		}
		.backend-remote-panel > div {
			width: 100%;
			justify-content: center;
		}
	}
	.style-percent {
		min-width: 38px;
		text-align: right;
	}
</style>
