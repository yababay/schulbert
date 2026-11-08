<script lang="ts">
    import { currentTrack } from '$lib/stores/editor.svelte';
    import { pageState } from '$lib/stores/player.svelte';

    let form: $state<HTMLFormElement | null> = null;
    let successAlert: $state<HTMLDivElement | null> = null;
    let errorAlert: $state<HTMLDivElement | null> = null;

    const handleSave = async () => {
        if (form) {
            const body = new FormData(form);
            const response = await fetch('/api/update', {
                method: 'POST',
                body
            });
            if (response.ok) {
                const modalElement = form.closest('.modal');
                if (modalElement) {
                    const modalInstance = bootstrap.Modal.getInstance(modalElement);
                    if (modalInstance) {
                        modalInstance.hide();      
                    }
                    successAlert?.classList.remove('d-none');
                    setTimeout(() => {
                        successAlert?.classList.add('d-none');
                    }, 3000);
                }
            } else {
                // Handle error response
                console.error('Failed to save track:', response.statusText);
                errorAlert?.classList.remove('d-none');
                setTimeout(() => {
                    errorAlert?.classList.add('d-none');
                }, 3000);
            }
        }
    };

</script>

<div class="modal-dialog">
    <div class="modal-content">
        <div class="modal-header">
            <h5 class="modal-title">Редактировать трек {currentTrack.playlist_id}-{currentTrack.track_number}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
        </div>
        <div class="modal-body">
            <form bind:this={form} class="d-flex flex-column gap-2">
                <div class="row mb-2">
                    <div class="col-6">
                        <label for="composers" class="form-label">Композиторы</label>
                    </div>
                    <div class="col-6">
                        <input name="composers" type="text" class="form-control mb-2" placeholder="Композиторы" bind:value={currentTrack.composers} />
                    </div>
                </div>
                <div class="row mb-2">
                    <div class="col-6">
                        <label for="artists" class="form-label">Исполнители</label>
                    </div>
                    <div class="col-6">
                        <input name="artists" type="text" class="form-control mb-2" placeholder="Исполнители" bind:value={currentTrack.artists} />
                    </div>
                </div>
                <div class="row mb-2">
                    <div class="col-6">
                        <label for="album" class="form-label">Альбом</label>
                    </div>
                    <div class="col-6">
                        <input name="album" type="text" class="form-control mb-2" placeholder="Альбом" bind:value={currentTrack.album} />
                    </div>
                </div>
                <div class="row mb-2">
                    <div class="col-6">
                        <label for="title" class="form-label">Трек</label>
                    </div>
                    <div class="col-6">
                        <input name="title" type="text" class="form-control mb-2" placeholder="Трек" bind:value={currentTrack.title} />
                    </div>
                </div>
                <input name="track_number" type="hidden" bind:value={currentTrack.track_number} />
                <input name="playlist_id" type="hidden" bind:value={currentTrack.playlist_id} />
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
            <button type="button" class="btn btn-primary" onclick={handleSave}>Сохранить</button>
        </div>
    </div>
</div>

<div class="alert alert-info mt-2 mb-0 small d-none" role="alert" bind:this={successAlert}>
    <strong>ОК:</strong> данные успешно сохранены.
</div>

<div class="alert alert-danger mt-2 mb-0 small d-none" role="alert" bind:this={errorAlert}>
    <strong>Ошибка:</strong> не удалось сохранить данные.
</div>

<style>
    .modal-body {
        max-height: 60vh;
        overflow-y: auto;
    }
    .alert {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1050;  
    }
</style>