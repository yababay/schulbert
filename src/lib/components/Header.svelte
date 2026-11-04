<script lang="ts">
    import Brand from './Brand.svelte';
    import Player from './Player.svelte';
    import Search from './Search.svelte';
    import Status from './Status.svelte';
    import Volume from './Volume.svelte';
</script>

<nav class="navbar bg-body-tertiary">
  <div class="container-fluid">
    <div class="d-flex align-items-center justify-content-between w-100">
        <Brand />
        <Search />
        <Player />
    </div>
    <div class="d-flex align-items-center justify-content-between w-100">
      <Status />
      <Volume />
    </div>
  </div>
</nav>
