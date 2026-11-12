<script lang="ts">
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const examples = $derived([
		{
			title: 'Search by imprint',
			description: 'Imprints match however they are typed, with look-alike characters tolerated.',
			url: `${data.apiBase}/v1/pills?imprint=M%20367`
		},
		{
			title: 'Narrow by shape and color',
			description: 'Repeat color (or comma-separate) for two-tone pills.',
			url: `${data.apiBase}/v1/pills?shape=capsule&color=yellow&color=white`
		},
		{
			title: 'One pill, with its label',
			description: 'Ingredients, packages, label images and a DailyMed link.',
			url: `${data.apiBase}/v1/pills/1`
		},
		{
			title: 'Colors and shapes',
			description: 'The vocabulary the search understands, with drawing colors.',
			url: `${data.apiBase}/v1/vocab`
		}
	]);

	const params = [
		['imprint', 'Text on the pill, any side, any order.'],
		['color', 'Color key; repeat for two-tone pills. See /v1/vocab.'],
		['shape', 'Shape key, e.g. round, oval, capsule (oblong).'],
		['size', 'Longest side in mm; matches ± size_tolerance (default 1).'],
		['score', 'Pieces the score lines make: 1 (none) to 4.'],
		['q', 'Drug, brand, ingredient or labeler name.'],
		['has_imprint', 'false for pills with no imprint.'],
		['group', 'true (default) collapses repackagers of the same pill.'],
		['limit, offset', 'Paging: limit 1–100 (default 24).']
	];
</script>

<svelte:head>
	<title>API · Pillmark</title>
	<meta name="description" content="Pillmark's free public API for pill identification." />
</svelte:head>

<div class="container page">
	<p class="eyebrow">Developers</p>
	<h1>A free, public pill API</h1>
	<p class="lead">
		JSON over HTTPS. No key, no sign-up. Built on FastAPI, so the full OpenAPI schema is always
		available{#if data.docsUrl}: <a href={data.docsUrl} rel="external">interactive docs</a>{/if}.
	</p>

	<div class="examples">
		{#each examples as example (example.url)}
			<section class="card example">
				<h2>{example.title}</h2>
				<p>{example.description}</p>
				<pre><code>curl '{example.url}'</code></pre>
			</section>
		{/each}
	</div>

	<section class="block">
		<h2>GET /v1/pills parameters</h2>
		<table>
			<tbody>
				{#each params as [name, text] (name)}
					<tr><th scope="row" class="mono">{name}</th><td>{text}</td></tr>
				{/each}
			</tbody>
		</table>
		<p class="note">
			Each result includes <span class="mono">match_score</span> (0–1),
			<span class="mono">group_size</span>, a <span class="mono">label_image_url</span> and, when
			the label has one, a <span class="mono">photo_url</span> of the pill. Other endpoints:
			<span class="mono">/v1/pills/&#123;id&#125;</span>,
			<span class="mono">/v1/pills/&#123;id&#125;/similar</span>,
			<span class="mono">/v1/labels/&#123;set_id&#125;</span>,
			<span class="mono">/v1/meta</span> and <span class="mono">/v1/health</span>.
		</p>
		<p class="note">
			Please be kind: cache responses (they carry <span class="mono">Cache-Control</span>) and keep
			it to a few requests a second. For bulk use, run your own copy; it's open source.
		</p>
	</section>
</div>

<style>
	.page {
		padding-top: 2.5rem;
	}
	.eyebrow {
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--accent);
	}
	h1 {
		margin: 0.35rem 0 0.75rem;
		font-size: clamp(2rem, 4vw, 2.75rem);
	}
	.lead {
		max-width: 62ch;
		font-size: 1.1rem;
		color: var(--ink-2);
	}
	.examples {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 460px), 1fr));
		gap: 1rem;
		margin-top: 2rem;
	}
	.example {
		padding: 1.1rem 1.2rem;
		min-width: 0;
	}
	.example h2 {
		font-size: 1.05rem;
	}
	.example p {
		margin: 0.25rem 0 0.75rem;
		color: var(--muted);
		font-size: 0.92rem;
	}
	pre {
		margin: 0;
		padding: 0.75rem 0.9rem;
		border-radius: var(--radius-sm);
		background: #16211d;
		color: #d8f3e8;
		font-size: 0.82rem;
		overflow-x: auto;
	}
	code {
		font-family: var(--mono);
	}
	.block {
		margin-top: 2.5rem;
	}
	.block h2 {
		font-size: 1.3rem;
		margin-bottom: 0.75rem;
	}
	table {
		width: 100%;
		max-width: 820px;
		border-collapse: collapse;
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}
	th,
	td {
		text-align: left;
		padding: 0.6rem 0.9rem;
		border-bottom: 1px solid var(--line);
		vertical-align: top;
	}
	th {
		width: 150px;
		font-weight: 700;
	}
	tr:last-child th,
	tr:last-child td {
		border-bottom: 0;
	}
	.note {
		max-width: 75ch;
		margin-top: 1rem;
		color: var(--ink-2);
	}
</style>
