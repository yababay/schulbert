<script lang="ts">
	import { state } from '../../routes/main.svelte';
	import logoImg from '$lib/assets/schulbert.svg';

	// =====================================================================
	// 🌟 РАЗМЕРЫ ЛОГОТИПА (Настройте эти цифры по вашему вкусу!)
	// =====================================================================
	const LOGO_WIDTH = "280"; 
	const LOGO_HEIGHT = "60";

	// Реактивно вычисляем состояние воспроизведения
	let isStopped = $derived(
		state.nowPlaying.includes("Воспроизведение остановлено") || 
		state.nowPlaying.trim() === "" || 
		state.nowPlaying.includes("Тишина")
	);
	
	let isPaused = $derived(state.nowPlaying.includes("[paused]"));
	
	// Флаг активного вращения диска: строго когда музыка играет (не стоп и не пауза)
	let isPlaying = $derived(!isStopped && !isPaused);

	// Очищаем строку статуса от технических маркеров [paused] для красивого вывода
	let cleanTrackTitle = $derived(state.nowPlaying.replace(" [paused]", ""));
</script>

<!-- ЛЕВАЯ ПАНЕЛЬ: ВАШ SVG ЛОГОТИП И ИНТЕРАКТИВНЫЙ СТАТУС -->
<div class="d-flex flex-column align-items-center align-items-md-start select-none">
	
	<!-- Изображение логотипа (Размеры регулируются переменными выше) -->
	<img 
		src={logoImg} 
		alt="Schubert Logo" 
		width={LOGO_WIDTH} 
		height={LOGO_HEIGHT} 
		class="img-fluid mb-2 style-brand-logo"
	/>
	
	<!-- Интерактивная статусная строка -->
	<p class="card-text mb-0 text-muted style-status-text">
		{#if isPlaying}
			<!-- Диск крутится ТОЛЬКО когда музыка играет -->
			<i class="bi bi-disc-fill text-primary animate-spin me-1"></i> 
			<span class="fw-semibold text-secondary">Сейчас играет:</span> {cleanTrackTitle}
		{:else if isPaused}
			<!-- При паузе диск замирает (нет класса animate-spin) -->
			<i class="bi bi-disc text-secondary me-1"></i> 
			<span class="fw-semibold text-secondary">Пауза:</span> {cleanTrackTitle}
		{:else}
			<!-- Когда полная тишина или стоп — показываем вашу красивую заглушку бренда, диск замер -->
			<i class="bi bi-music-note text-muted me-1"></i> 
			<span class="text-secondary fw-medium">Музыкальный ассистент «Шульберт»</span>
		{/if}
	</p>

</div>

<style>
	/* Тонкая настройка шрифта статуса */
	.style-status-text {
		font-size: 0.85rem;
		min-height: 1.25rem;
		transition: color 0.3s ease;
	}
	
	/* Защита от выделения текста при кликах */
	.select-none {
		user-select: none;
	}

	/* CSS-анимация вращения диска */
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	:global(.animate-spin) {
		display: inline-block;
		animation: spin 4s linear infinite;
	}
</style>
