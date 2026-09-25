<script lang="ts">
	import { state as pageState, actions } from '../../routes/main.svelte';

	let isStopped = $derived(pageState.nowPlaying.includes("Воспроизведение остановлено") || pageState.nowPlaying.trim() === "");
	let localIsPlaying = $state(false);
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

	function handlePlayPauseToggle() {
		if (localIsPlaying) {
			actions.sendMpcCommand({ action: 'pause' });
			localIsPlaying = false;
		} else {
			actions.sendMpcCommand({ action: 'play' });
			localIsPlaying = true;
		}
	}

	function handleStop() {
		actions.sendMpcCommand({ action: 'stop' });
		localIsPlaying = false;
		pageState.nowPlaying = "Воспроизведение остановлено или очередь пуста.";
	}

	// Функция обработки изменения ползунка громкости
	function handleVolumeChange(event: Event) {
		const target = event.target as HTMLInputElement;
		const newVolume = target.value;
		// Отправляем абсолютное значение (например, "65") на бэкенд
		actions.sendMpcCommand({ volume: newVolume });
	}
</script>

<!-- ОБЪЕДИНЕННАЯ ПРАВАЯ ПАНЕЛЬ С УМНЫМ RANGE ПОЛЗУНКОМ -->
<div class="d-flex flex-column flex-sm-row align-items-center gap-3 backend-remote-panel">
	
	<!-- Группа управления треками (строгие иконки) -->
	<div class="btn-group shadow-sm" role="group">
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

		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title="Остановить воспроизведение и сбросить очередь"
			onclick={handleStop}
		>
			<i class="bi bi-stop-fill fs-5"></i>
		</button>

		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title="Перейти к следующему треку"
			onclick={() => actions.sendMpcCommand({ action: 'next' })}
		>
			<i class="bi bi-skip-forward-fill fs-5"></i>
		</button>
	</div>

	<!-- 🌟 НОВЫЙ СТРОГИЙ BOOTSTRAP RANGE ПОЛЗУНОК ГРОМКОСТИ -->
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
			onchange={handleVolumeChange}
			title={`Громкость: ${pageState.volume}%`}
		/>
		<span class="small font-monospace text-secondary style-percent">{pageState.volume}%</span>
	</div>

</div>

<style>
	/* Небольшая фиксация ширины для мобильных */
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
