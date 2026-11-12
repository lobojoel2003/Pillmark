<script lang="ts">
	import '../app.css';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Logo from '#lib/components/Logo.svelte';
	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	const nav = [
		{ href: resolve('/'), label: 'Identify' },
		{ href: resolve('/about'), label: 'About' },
		{ href: resolve('/developers'), label: 'API' }
	];
	const count = (n: number) => n.toLocaleString('en-US');
	const dataset = $derived(data.meta?.dataset);
</script>

<a class="skip" href="#main">Skip to content</a>

<header class="site">
	<div class="container bar">
		<a class="home" href={resolve('/')} aria-label="Pillmark home"><Logo /></a>
		<nav aria-label="Main">
			{#each nav as item (item.href)}
				<a href={item.href} aria-current={page.url.pathname === item.href ? 'page' : undefined}
					>{item.label}</a
				>
			{/each}
		</nav>
		<a class="poison" href="tel:18002221222">
			<span class="label">Poison Control</span>
			<span class="number">1-800-222-1222</span>
		</a>
	</div>
</header>

<main id="main">
	{@render children()}
</main>

<footer class="site">
	<div class="container foot">
		<p>
			<strong>Pillmark</strong> is an open pill identifier. Data: FDA drug labels from
			<a href="https://dailymed.nlm.nih.gov/" rel="external">DailyMed</a>, U.S. National Library of
			Medicine{#if dataset}
				, {count(dataset.pills)} pills from {count(dataset.labels)} labels{/if}. Not medical advice.
		</p>
		<p class="version">
			<a href="https://github.com/lobojoel2003/Pillmark" rel="external">Source</a>
			<span aria-hidden="true">·</span>
			<span title={`commit ${__APP_COMMIT__}`}>v{__APP_VERSION__} (build {__APP_BUILD__})</span>
			{#if data.meta}
				<span aria-hidden="true">·</span>
				<span>API v{data.meta.version} (build {data.meta.build})</span>
			{/if}
		</p>
	</div>
</footer>

<style>
	.skip {
		position: absolute;
		left: -999px;
		top: 0.5rem;
		z-index: 10;
		padding: 0.5rem 0.9rem;
		border-radius: 999px;
		background: var(--accent);
		color: var(--accent-ink);
	}
	.skip:focus {
		left: 0.5rem;
	}
	header.site {
		position: sticky;
		top: 0;
		z-index: 5;
		background: color-mix(in srgb, var(--bg) 88%, transparent);
		backdrop-filter: saturate(1.4) blur(10px);
		border-bottom: 1px solid var(--line);
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		min-height: 64px;
	}
	.home {
		text-decoration: none;
	}
	nav {
		display: flex;
		gap: 0.25rem;
	}
	nav a {
		padding: 0.4rem 0.75rem;
		border-radius: 999px;
		color: var(--ink-2);
		font-weight: 600;
		font-size: 0.95rem;
		text-decoration: none;
	}
	nav a:hover {
		background: var(--surface-2);
	}
	nav a[aria-current='page'] {
		color: var(--ink);
		background: var(--surface-2);
	}
	.poison {
		margin-left: auto;
		display: inline-flex;
		flex-direction: column;
		align-items: flex-end;
		line-height: 1.15;
		padding: 0.35rem 0.85rem;
		border-radius: 12px;
		background: var(--danger-soft);
		color: var(--danger);
		text-decoration: none;
	}
	.poison .label {
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.poison .number {
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}
	main {
		min-height: calc(100vh - 64px - 120px);
	}
	footer.site {
		margin-top: 4rem;
		border-top: 1px solid var(--line);
		color: var(--muted);
		font-size: 0.85rem;
	}
	.foot {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0.75rem 2rem;
		padding-block: 1.5rem 2rem;
	}
	.foot a {
		color: inherit;
	}
	.version {
		font-variant-numeric: tabular-nums;
	}
	@media (max-width: 640px) {
		header.site {
			position: static;
		}
		.bar {
			flex-wrap: wrap;
			gap: 0.25rem 1rem;
			padding-block: 0.5rem;
		}
		nav {
			order: 3;
			width: 100%;
			margin-left: -0.75rem;
		}
		.poison {
			padding: 0.3rem 0.6rem;
		}
	}
</style>
