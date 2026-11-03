<script lang="ts">
    import Brand from './Brand.svelte';
    import Search from './Search.svelte';
    import Status from './Status.svelte';
</script>

<nav class="navbar bg-body-tertiary">
  <div class="container-fluid">
    <div class="d-flex align-items-center justify-content-between w-100">
        <Brand />
        <Search />
    </div>
    <Status />
  </div>
</nav>
