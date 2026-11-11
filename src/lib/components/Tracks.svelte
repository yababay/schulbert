<script lang="ts">
	import { onMount } from 'svelte';
    import {rows, query, hasComposers} from '$lib/stores/search.svelte';
    import Row from '$lib/components/Row.svelte';
    import Card from '$lib/components/Card.svelte';
    import Editor from '$lib/components/Editor.svelte';
    
    const { bootstrap } = window as any;

	onMount(() => {
		const lastPlaylist = localStorage.getItem('lastPlaylist');
		$query = lastPlaylist || '';
	});

    let editor = $state<HTMLDivElement | null>(null);
    let modal: any = null;
    
    const showEditor = () => {
        if(!modal) modal = new bootstrap.Modal(editor);
        modal.show();
    };

    let successAlert = $state<HTMLDivElement | null>(null);
    let errorAlert = $state<HTMLDivElement | null>(null);

    const showAlert = (alert: HTMLDivElement | null) => {
        if(alert) {
            alert.classList.remove('d-none');
            setTimeout(() => {
                alert?.classList.add('d-none');
            }, 3000);
        }
    };

    const showSuccessAlert = () => showAlert(successAlert);
    const showErrorAlert = () => showAlert(errorAlert);

</script>

{#if $rows.length > 0}
    <div class="d-flex d-md-none flex-column gap-2">
        {#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
            <Card {composers} {artists} {album} {title} {playlist_id} {track_number} />
        {/each}
    </div>
    <table class="table table-striped d-none d-md-table">
        <thead>
            <tr>
                <th class:d-none={!$hasComposers}>Композитор</th>
                <th>Исполнитель</th>
                <th>Альбом</th>
                <th>Трек</th>
                <th style="width: 100px" class="text-center pe-0 ps-0">Действия</th>
            </tr>
        </thead>
        <tbody>
            {#each $rows as {composers, artists, album, title, playlist_id, track_number} (playlist_id + '-' + track_number)}
                <Row {composers} {artists} {album} {title} {playlist_id} {track_number} {showEditor} />
            {/each}
        </tbody>
    </table>

    <div class="modal" tabindex="-1" bind:this={editor}>
		<Editor {showSuccessAlert} {showErrorAlert} />
    </div>

{/if}

<div class="alert alert-info mt-2 mb-0 small d-none" role="alert" bind:this={successAlert}>
    <strong>ОК:</strong> данные успешно сохранены.
</div>

<div class="alert alert-danger mt-2 mb-0 small d-none" role="alert" bind:this={errorAlert}>
    <strong>Ошибка:</strong> не удалось сохранить данные.
</div>
