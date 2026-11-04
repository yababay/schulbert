<script lang="ts">
    import { query } from '$lib/stores/search.svelte';
</script>

<div class="d-flex w-50" role="search">
    <input class="form-control me-2" type="search" bind:value={$query} 
    placeholder="Трек, альбом, композитор или исполнитель" aria-label="Поиск" />
</div>
