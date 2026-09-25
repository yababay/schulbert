// Базовый URL для прокси-запросов Nginx
const API_BASE = '/api';

export const pageState = $state({
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
                pageState.playlists = data.playlists || [];
            }
        } catch (e) {
            console.error("Ошибка загрузки плейлистов:", e);
        }
    },

    // 2. Загрузка правой панели: Треки конкретного плейлиста
    async fetchTracks(playlistId: number, playlistName: string) {
        pageState.selectedPlaylistId = playlistId;
        pageState.selectedPlaylistName = playlistName;
        try {
            const res = await fetch(`${API_BASE}/catalog?id=${playlistId}`);
            if (res.ok) {
                const data = await res.json();
                pageState.currentTracks = data.tracks || [];
            }
        } catch (e) {
            console.error("Ошибка загрузки треков:", e);
        }
    },

    // 3. Отправка быстрых REST-команд управления в mpc
    async sendMpcCommand(params: { action?: string; volume?: string; load?: number; track?: number }) {
        const url = new URL(`${window.location.origin}${API_BASE}/mpc`);
        if (params.action) url.searchParams.append('action', params.action);
        if (params.volume) url.searchParams.append('volume', params.volume);
        if (params.load) url.searchParams.append('load', params.load.toString());
        if (params.track) url.searchParams.append('track', params.track.toString());

        try {
            const res = await fetch(url.toString(), { method: 'POST' });
            if (res.ok) {
                if (params.volume && !params.volume.startsWith('+') && !params.volume.startsWith('-')) {
                    pageState.volume = parseInt(params.volume);
                }
                await this.updateStatus();
            }
        } catch (e) {
            console.error("Ошибка отправки команды mpc:", e);
        }
    },

    // 4. Опрос статуса текущей песни
    async updateStatus() {
        try {
            const res = await fetch(`${API_BASE}/mpc?action=status`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    pageState.nowPlaying = data.track || 'Воспроизведение остановлено или очередь пуста.';
                    if (data.volume !== undefined) {
                        pageState.volume = data.volume;
                    }
                }
            }
        } catch (e) {
            console.error("Ошибка обновления статуса:", e);
        }
    }
};
