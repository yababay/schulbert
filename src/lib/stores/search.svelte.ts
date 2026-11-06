import { derived, writable } from 'svelte/store';
import _TRACKS from '$lib/assets/tracks.csv?raw';
import Papa from 'papaparse';
import { pageState } from '$lib/stores/player.svelte';

export interface Track {
    composers: string;
    album: string;
    title: string;
    artists: string;
    playlist_id: number;
    track_number: number;
    is_current?: boolean
}

const TRACKS_ARRAY = _TRACKS.split('\n');
const HEADER = TRACKS_ARRAY[0];
const TRACKS = TRACKS_ARRAY.slice(1);
const RAW_TRACKS = TRACKS.filter(line => !!line.trim());

const filteredTracks = (track: string): Track[] => {
    if (typeof track !== 'string') return [];
    let trackObj: Track[] = [];
    track = `${HEADER}\n${track}`.trim();
    Papa.parse(track, {
        header: true,
        skipEmptyLines: true,
        dynamicTyping: true, // Автоматически превратит id и номера треков в числа
        complete: (results) => {
            trackObj = results.data as Track[];
        }
    });
    const current = trackObj.find(({title}) => pageState.nowPlaying.includes(title));
    if(current) current.is_current = true;
    return trackObj;
};

export const query = writable<string>('');

export const rows = derived(query, ($query: string) => {
    if(/^[\d]{4}$/.test($query.trim())) {
        const lines = RAW_TRACKS.filter(line => new RegExp(`\\,${$query}\\,\\d+$`).test(line)).join('\n');
        return filteredTracks(lines)
    }
    if($query.trim().length > 2) {
        const lowerQuery = $query.trim().toLocaleLowerCase();
        const tracks = RAW_TRACKS.filter(line => {
            return line.toLocaleLowerCase().includes(lowerQuery);
        });
        return filteredTracks(tracks.join('\n'));
    }
    return []
});
