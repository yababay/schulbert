<script lang="ts">
	import { pageState, sendMpcCommand } from '$lib/stores/player.svelte';
</script>

	
<!-- Группа управления треками -->
<div class="btn-group shadow-sm cursor-pointer" role="group">
	
	<!-- Динамическая кнопка Play/Pause (Сверяется со сквозным статусом isPlaying) -->
	<button 
		type="button" 
		class="btn btn-outline-dark py-1 px-2 py-md-2 px-md-3 d-flex align-items-center" 
		title={pageState.isPaused ? "Запустить воспроизведение" : "Поставить на паузу"}
		onclick={() => sendMpcCommand({ action: pageState.isPaused ? 'play' : 'pause' })}
	>
		{#if pageState.isPaused}
			<i class="bi bi-play-fill fs-5"></i>
		{:else}
			<i class="bi bi-pause-fill fs-5"></i>
		{/if}
	</button>

	<!-- Кнопка Следующий трек -->
	<button 
		type="button" 
		class="btn btn-outline-dark py-1 px-2 py-md-2 px-md-3 d-flex align-items-center" 
		title="Перейти к следующему треку"
		onclick={() => sendMpcCommand({ action: 'next' })}
	>
		<i class="bi bi-skip-forward-fill fs-5"></i>
	</button>
</div>
