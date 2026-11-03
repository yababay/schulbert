<script lang="ts">
    import { query } from '$lib/stores/search.svelte';
</script>

<div class="d-flex w-50" role="search">
    <input class="form-control me-2" type="search" bind:value={$query} placeholder="Введите название трека, альбома, композитора или исполнителя" aria-label="Поиск" />
</div>
