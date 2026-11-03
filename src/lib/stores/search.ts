import { writable } from 'svelte/store';

export interface Track {
    composers: string;
    album: string;
    title: string;
    artists: string;
    playlist_id: number;
    track_number: number;
}

export const rows = writable<Track[]>([]);