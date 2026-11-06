<script lang="ts">
    import Brand from './Brand.svelte';
    import Player from './Player.svelte';
    import Search from './Search.svelte';
    import Status from './Status.svelte';
    import Volume from './Volume.svelte';
</script>

<header class="header w-100 bg-body-tertiary">
  <div class="container-fluid">
    <div class="d-flex align-items-center justify-content-between w-100" id="brand-search-player-row">
      <Brand />
      <Search />
      <Player />
    </div>
    <div class="row g-2" id="status-volume-row">
      <div class="col-12 col-md-9 d-flex align-items-center justify-content-start">
        <Status />
      </div>
      <div class="col-12 col-md-3 d-flex align-items-center justify-content-end">
        <Volume />
      </div>
    </div> 
  </div>
</header>
