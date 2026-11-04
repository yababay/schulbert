<script lang="ts">
	import { pageState, actions } from '$lib/stores/player.svelte';

	// 1. Реактивно вычисляем состояние Полного Стопа / Тишины
	let isStopped = $derived(
		pageState.nowPlaying.includes("Воспроизведение остановлено") || 
		pageState.nowPlaying.trim() === "" ||
		pageState.nowPlaying.includes("Тишина")
	);
	
	// 2. Реактивно вычисляем состояние Паузы
	let isPaused = $derived(pageState.nowPlaying.includes("[paused]"));

	// 3. 🌟 ГЛОБАЛЬНЫЙ МАРКЕР ВОСПРОИЗВЕДЕНИЯ: Музыка играет, если это не Стоп и не Пауза!
	// Теперь это свойство мгновенно реагирует на любые изменения в pageState.nowPlaying
	let isPlaying = $derived(!isStopped && !isPaused);

	// Умный тогл Play/Pause
	function handlePlayPauseToggle() {
		if (isPlaying) {
			// Если сейчас играет — ставим на паузу
			actions.sendMpcCommand({ action: 'pause' });
		} else {
			// Если стояло на паузе или было остановлено — запускаем играть
			actions.sendMpcCommand({ action: 'play' });
		}
	}

	// Нажатие на кнопку Стоп принудительно гасит тракт
	function handleStop() {
		actions.sendMpcCommand({ action: 'stop' });
		pageState.nowPlaying = "Воспроизведение остановлено или очередь пуста.";
	}
</script>

	
	<!-- Группа управления треками -->
	<div class="btn-group shadow-sm" role="group">
		
		<!-- Динамическая кнопка Play/Pause (Сверяется со сквозным статусом isPlaying) -->
		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title={isPlaying ? "Поставить на паузу" : "Запустить воспроизведение"}
			onclick={handlePlayPauseToggle}
		>
			{#if isPlaying}
				<i class="bi bi-pause-fill fs-5"></i>
			{:else}
				<i class="bi bi-play-fill fs-5"></i>
			{/if}
		</button>

		<!-- Кнопка Стоп (Появляется реактивно) -->
		<!-- #if !isStopped -->
			<button 
				type="button" 
				class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
				class:d-none={!isPlaying}
				title="Остановить воспроизведение и сбросить очередь"
				onclick={handleStop}
			>
				<i class="bi bi-stop-fill fs-5"></i>
			</button>
		<!-- {/if} -->

		<!-- Кнопка Следующий трек -->
		<button 
			type="button" 
			class="btn btn-outline-dark py-2 px-3 d-flex align-items-center" 
			title="Перейти к следующему треку"
			onclick={() => actions.sendMpcCommand({ action: 'next' })}
		>
			<i class="bi bi-skip-forward-fill fs-5"></i>
		</button>
	</div>
