import { derived, writable } from 'svelte/store';
import TRACKS from '$lib/assets/tracks.csv?raw';
import Papa from 'papaparse';

let allTracks = new Array<Track>();

Papa.parse(TRACKS, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true, // Автоматически превратит id и номера треков в числа
    complete: (results) => {
        allTracks = results.data as Track[];
    }
});

export const query = writable<string | number>('');

export interface Track {
    composers: string;
    album: string;
    title: string;
    artists: string;
    playlist_id: number;
    track_number: number;
}

export const rows = derived(query, ($query: string | number) => {
    if(typeof $query === 'number' && $query > 999) {
        return allTracks.filter(t => t.playlist_id === $query);
    }
    if(typeof $query === 'string' && $query.trim().length > 2) {
        const lowerQuery = $query.trim().toLowerCase();
        const filteredTracks = allTracks.filter(track => {
            const { composers, album, title, artists } = track;
            return (typeof composers === 'string' && composers.toLowerCase().includes(lowerQuery)) ||
                (typeof album === 'string' && album.toLowerCase().includes(lowerQuery)) ||
                (typeof title === 'string' && title.toLowerCase().includes(lowerQuery)) ||
                (typeof artists === 'string' && artists.toLowerCase().includes(lowerQuery));
        });
        return filteredTracks;
    }
    return []
});
