<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import PillGlyph from '#lib/components/PillGlyph.svelte';
</script>

<svelte:head><title>{page.status} · Pillmark</title></svelte:head>

<div class="container error">
	<PillGlyph shape="round" muted size={140} label="" />
	<h1>{page.status === 404 ? 'Nothing here' : 'Something went wrong'}</h1>
	<p>{page.error?.message ?? 'Please try again.'}</p>
	<a class="button primary" href={resolve('/')}>Identify a pill</a>
</div>

<style>
	.error {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.9rem;
		padding-top: 4rem;
		text-align: center;
	}
	p {
		color: var(--muted);
	}
</style>
