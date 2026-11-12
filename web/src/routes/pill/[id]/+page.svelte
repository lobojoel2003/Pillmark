<script lang="ts">
	import { resolve } from '$app/paths';
	import LabelPhoto from '#lib/components/LabelPhoto.svelte';
	import PillGlyph from '#lib/components/PillGlyph.svelte';
	import SafetyNotice from '#lib/components/SafetyNotice.svelte';
	import { pillTitle } from '#lib/api.ts';
	import { colorOf, describePill, shapeOf } from '#lib/vocab.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const pill = $derived(data.pill);
	const title = $derived(pillTitle(pill));
	const description = $derived(describePill(pill.shape, pill.colors, pill.imprint || null));
	const colorText = $derived(pill.colors.map((c) => colorOf(c)?.label ?? c).join(' and ') || '—');
	const shapeText = $derived(pill.shape ? (shapeOf(pill.shape)?.label ?? pill.shape) : '—');
	const scoreText = $derived(
		!pill.score || pill.score === 1 ? 'None' : `Splits into ${pill.score} pieces`
	);
	const backHref = $derived(
		resolve(
			`/?${new URLSearchParams([
				...(pill.imprint ? [['imprint', pill.imprint]] : []),
				...(pill.shape ? [['shape', pill.shape]] : []),
				...pill.colors.map((c) => ['color', c])
			])}`
		)
	);
	const date = (value: string | null) =>
		value
			? new Date(`${value}T00:00:00Z`).toLocaleDateString('en-US', {
					year: 'numeric',
					month: 'short',
					day: 'numeric',
					timeZone: 'UTC'
				})
			: null;
</script>

<svelte:head>
	<title>{title} {pill.strength ?? ''} · imprint {pill.imprint || 'none'} · Pillmark</title>
	<meta
		name="description"
		content={`${description}. ${title} ${pill.strength ?? ''} by ${pill.labeler ?? 'unknown labeler'}.`}
	/>
</svelte:head>

<article class="container detail">
	<a class="back" href={backHref}>← Back to search</a>

	<div class="hero">
		<div class="visuals card">
			<figure class="drawing">
				<PillGlyph
					shape={pill.shape}
					colors={pill.colors}
					sides={pill.imprint_sides}
					score={pill.score}
					form={pill.dosage_form}
					sizeMm={pill.size_mm}
					size={240}
					label={description}
				/>
				<figcaption>Drawing from the label's description</figcaption>
			</figure>
			{#if pill.photo_url}
				<LabelPhoto
					src={pill.photo_url}
					alt={`Photo of ${title}`}
					width={240}
					height={240}
					caption="Pill photo"
				/>
			{/if}
			<LabelPhoto
				src={pill.label_image_url}
				alt={`Package label of ${title}`}
				width={240}
				height={240}
				caption="Package label"
			/>
		</div>

		<div class="summary">
			<div class="tags">
				{#if pill.dea_schedule}<span class="tag warn">Controlled substance {pill.dea_schedule}</span
					>{/if}
				{#if !pill.marketed}<span class="tag">Discontinued</span>{/if}
				{#if pill.label.kind === 'otc'}<span class="tag accent">Over the counter</span>{/if}
				{#if pill.label.kind === 'rx'}<span class="tag accent">Prescription</span>{/if}
			</div>
			<h1>{title}</h1>
			<p class="strength">{pill.strength ?? ''} {pill.dosage_form?.toLowerCase() ?? ''}</p>
			{#if pill.generic_name}<p class="generic">{pill.generic_name}</p>{/if}

			<dl class="facts">
				<div>
					<dt>Imprint</dt>
					<dd class="mono">
						{#if pill.imprint_sides.length}
							{#each pill.imprint_sides as side, i (i)}<span class="side">{side}</span>{/each}
						{:else}None{/if}
					</dd>
				</div>
				<div>
					<dt>Color</dt>
					<dd>{colorText}</dd>
				</div>
				<div>
					<dt>Shape</dt>
					<dd>{shapeText}</dd>
				</div>
				<div>
					<dt>Size</dt>
					<dd>{pill.size_mm ? `${pill.size_mm} mm` : '—'}</dd>
				</div>
				<div>
					<dt>Score</dt>
					<dd>{scoreText}</dd>
				</div>
				<div>
					<dt>Route</dt>
					<dd>{pill.route?.toLowerCase() ?? '—'}</dd>
				</div>
				<div>
					<dt>Labeler</dt>
					<dd>{pill.labeler ?? '—'}</dd>
				</div>
				<div>
					<dt>NDC</dt>
					<dd class="mono">{pill.product_code ?? '—'}</dd>
				</div>
			</dl>

			<div class="actions">
				<a
					class="button primary"
					href={pill.label.dailymed_url}
					rel="external noopener"
					target="_blank">Full label on DailyMed ↗</a
				>
			</div>
			<SafetyNotice compact />
		</div>
	</div>

	{#if pill.ingredients.length}
		<section class="block">
			<h2>Active ingredients</h2>
			<table>
				<thead
					><tr
						><th scope="col">Ingredient</th><th scope="col">Strength</th><th scope="col">UNII</th
						></tr
					></thead
				>
				<tbody>
					{#each pill.ingredients as ingredient (ingredient.name)}
						<tr>
							<td>{ingredient.name}</td>
							<td>{ingredient.strength ?? '—'}</td>
							<td class="mono">{ingredient.unii ?? '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
	{/if}

	<section class="block">
		<h2>Label</h2>
		<dl class="facts wide">
			<div>
				<dt>Published</dt>
				<dd>{date(pill.label.effective_date) ?? '—'}</dd>
			</div>
			<div>
				<dt>Version</dt>
				<dd>{pill.label.version}</dd>
			</div>
			{#if pill.marketing_start}<div>
					<dt>On the market since</dt>
					<dd>{date(pill.marketing_start)}</dd>
				</div>{/if}
			{#if pill.marketing_end}<div>
					<dt>Discontinued</dt>
					<dd>{date(pill.marketing_end)}</dd>
				</div>{/if}
			<div>
				<dt>Set id</dt>
				<dd class="mono small">{pill.set_id}</dd>
			</div>
			{#if pill.packages.length}<div>
					<dt>Packages</dt>
					<dd class="mono small">{pill.packages.join(', ')}</dd>
				</div>{/if}
		</dl>
	</section>

	{#if data.similar.length}
		<section class="block">
			<h2>
				Same pill from {data.similar.length} other {data.similar.length === 1
					? 'labeler'
					: 'labelers'}
			</h2>
			<p class="hint">
				Repackagers and distributors selling this exact pill under their own label.
			</p>
			<ul class="others">
				{#each data.similar as other (other.id)}
					<li>
						<a href={resolve('/pill/[id]', { id: String(other.id) })}>
							<span>{other.labeler ?? 'Unknown labeler'}</span>
							<span class="mono small">{other.product_code}</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</article>

<style>
	.detail {
		padding-top: 1.25rem;
	}
	.back {
		display: inline-block;
		margin-bottom: 1rem;
		font-weight: 600;
		text-decoration: none;
	}
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
		gap: 2rem;
		align-items: start;
	}
	.visuals {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 1rem;
		padding: 1.25rem;
	}
	.drawing {
		margin: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 240px;
		height: 240px;
		border-radius: var(--radius-sm);
		background: radial-gradient(circle at 50% 40%, var(--surface) 0%, var(--surface-2) 75%);
		border: 1px solid var(--line);
		position: relative;
	}
	.drawing figcaption {
		position: absolute;
		bottom: 0.5rem;
		font-size: 0.7rem;
		color: var(--muted);
	}
	.summary {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	h1 {
		font-size: clamp(1.8rem, 3.5vw, 2.5rem);
		overflow-wrap: anywhere;
	}
	.strength {
		font-size: 1.15rem;
		font-weight: 700;
		color: var(--ink-2);
	}
	.generic {
		color: var(--muted);
		margin-top: -0.4rem;
	}
	.facts {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem 1.25rem;
		margin: 0.5rem 0;
	}
	.facts.wide {
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
	}
	dt {
		font-size: 0.78rem;
		font-weight: 700;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	dd {
		margin: 0.1rem 0 0;
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.side {
		display: inline-block;
		margin: 0 0.35rem 0.2rem 0;
		padding: 0.05rem 0.5rem;
		border-radius: 6px;
		background: var(--surface-2);
		border: 1px solid var(--line);
	}
	.small {
		font-size: 0.85rem;
	}
	.actions {
		display: flex;
		gap: 0.6rem;
		flex-wrap: wrap;
		margin: 0.25rem 0 0.5rem;
	}
	.block {
		margin-top: 2.5rem;
	}
	.block h2 {
		font-size: 1.3rem;
		margin-bottom: 0.75rem;
	}
	.hint {
		color: var(--muted);
		margin: -0.4rem 0 0.75rem;
		font-size: 0.9rem;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		overflow: hidden;
		font-size: 0.95rem;
	}
	th,
	td {
		text-align: left;
		padding: 0.65rem 0.9rem;
		border-bottom: 1px solid var(--line);
	}
	th {
		background: var(--surface-2);
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
	}
	tr:last-child td {
		border-bottom: 0;
	}
	.others {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.others a {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.65rem 0.9rem;
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--ink);
		text-decoration: none;
	}
	.others a:hover {
		border-color: var(--accent);
	}
	@media (max-width: 900px) {
		.hero {
			grid-template-columns: 1fr;
		}
	}
</style>
