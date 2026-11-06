<script lang="ts">
	import logo from '$lib/assets/schulbert.svg';
	import icon from '$lib/assets/favicon.svg';
	import { PUBLIC_PAGE_TITLE } from '$env/static/public';

	const alt = PUBLIC_PAGE_TITLE;
	const title = PUBLIC_PAGE_TITLE;

</script>

<img src={icon} {alt} {title} class="brand-icon" />
<img src={logo} {alt} {title} width="280" height="60" class="brand-logo" />

<style>
	.brand-icon {
		display: none; 
		height: 100%;
		max-height: 44px;
		width: auto;
	}

	@media (max-width: 767.98px) {
		.brand-icon {
			display: block;
		}

		.brand-logo {
			display: none;
		}
	}
</style>
