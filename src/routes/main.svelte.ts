import { state as devState } from './main.svelte'; // Сохраняем структуру, если нужно

// Базовый URL для прокси-запросов Nginx
const API_BASE = '/api';

export const state = $state({
    playlists: [] as Array<{ playlist_id: number; name: string }>,
    currentTracks: [] as Array<{ track_number: number; title: string; artist: string; album: string }>,
    selectedPlaylistId: null as number | null,
    selectedPlaylistName: '' as string,
    
    // Поля фильтрации
    selectedGenre: { title: "Все жанры", min: 0, max: 99999 },
    searchQuery: '',
    
    // Сейчас играет (информация с Cubi)
    nowPlaying: 'Воспроизведение остановлено или очередь пуста.',
    volume: 50
});

export const actions = {
    // 1. Загрузка левой панели: Индекс всех плейлистов
    async fetchPlaylists() {
        try {
            const res = await fetch(`${API_BASE}/catalog`);
            if (res.ok) {
                const data = await res.json();
                state.playlists = data.playlists || [];
            }
        } catch (e) {
            console.error("Ошибка загрузки плейлистов:", e);
        }
    },

    // 2. Загрузка правой панели: Треки конкретного плейлиста
    async fetchTracks(playlistId: number, playlistName: string) {
        state.selectedPlaylistId = playlistId;
        state.selectedPlaylistName = playlistName;
        try {
            const res = await fetch(`${API_BASE}/catalog?id=${playlistId}`);
            if (res.ok) {
                const data = await res.json();
                state.currentTracks = data.tracks || [];
            }
        } catch (e) {
            console.error("Ошибка загрузки треков:", e);
        }
    },

    async sendMpcCommand(params: { action?: string; volume?: string; load?: number; track?: number }) {
        const url = new URL(`${window.location.origin}/api/mpc`);
        if (params.action) url.searchParams.append('action', params.action);
        if (params.volume) url.searchParams.append('volume', params.volume);
        if (params.load) url.searchParams.append('load', params.load.toString());
        if (params.track) url.searchParams.append('track', params.track.toString());

        try {
            const res = await fetch(url.toString(), { method: 'POST' });
            if (res.ok) {
                // Если мы устанавливали абсолютную громкость ползунком, 
                // локально обновляем значение сразу, чтобы интерфейс не дергался
                if (params.volume && !params.volume.startsWith('+') && !params.volume.startsWith('-')) {
                    state.volume = parseInt(params.volume);
                }
                await this.updateStatus();
            }
        } catch (e) {
            console.error("Ошибка отправки команды mpc:", e);
        }
    },

    async updateStatus() {
        try {
            const res = await fetch('/api/mpc?action=status', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    state.nowPlaying = data.track || 'Тишина.';
                    
                    // 🌟 ПАРСИМ ГРОМКОСТЬ, КОТОРУЮ НАМ ТЕПЕРЬ ВОЗВРАЩАЕТ СЕРВЕР CUBI
                    if (data.volume !== undefined) {
                        state.volume = data.volume;
                    }
                }
            }
        } catch (e) {
            console.error("Ошибка обновления статуса:", e);
        }
    }
};
