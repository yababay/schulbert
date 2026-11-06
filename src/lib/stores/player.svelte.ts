import { PUBLIC_STANUS_UPDATE_INTERVAL, PUBLIC_NO_TRACKS_MESSAGE } from '$env/static/public';

const statusUpdateInterval = parseInt(PUBLIC_STANUS_UPDATE_INTERVAL) || 5000;

export const pageState = $state({
    nowPlaying: PUBLIC_NO_TRACKS_MESSAGE,
    isPaused: true,
    volume: 50
});

// Отправка быстрых REST-команд управления в mpc
export const sendMpcCommand = async (params: { action?: string; volume?: string; load?: number; track?: number }) => {
    let { action, volume, load, track } = params;
    const url = new URL(`${window.location.origin}/api/mpc`);
    if(!track) track = 1;
    if(!volume) volume = '50';
    if(!action) action = 'status';
    let status = null;
    switch (action) {
        case 'load':
            if (typeof load !== 'number') throw new Error("Load parameter must be a number.");
            url.searchParams.append('load', load.toString());
            url.searchParams.append('track', track.toString());
            status = await fetch(url.toString());
            await updateStatus();
            break;
        case 'volume':
            url.searchParams.append('volume', volume.toString());
            status = await fetch(url.toString());
            pageState.volume = parseInt(volume);
            break;
        default:
            url.searchParams.append('action', action.toString());
            status = await fetch(url.toString());
            if(action === 'start' || action === 'next' || action === 'prev' || action === 'stop' || action === 'pause') {
                await updateStatus();
            }   
            break;
    }
    return status;
 }

// Опрос статуса текущей песни
const updateStatus = async () => {
        try {
            const res = await sendMpcCommand({ action: 'status' });
            if (res.ok) {
                const data = await res.json();
                // console.log("Статус обновлен:", data);
                if (data.status === "success") {
                    pageState.isPaused = !data.track || data.track.includes("[paused]");
                    pageState.nowPlaying = data.track && data.track.replace(/\[paused\]/, '') || PUBLIC_NO_TRACKS_MESSAGE;
                    if (data.volume !== undefined) {
                        pageState.volume = data.volume;
                    }
                }
            }
        } catch (e) {
            console.error("Ошибка обновления статуса:", e);
        }
}

setInterval(updateStatus, statusUpdateInterval);
