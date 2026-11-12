<script lang="ts">
	import { resolve } from '$app/paths';
	import LabelPhoto from './LabelPhoto.svelte';
	import PillGlyph from './PillGlyph.svelte';
	import { matchLabel, pillTitle, type PillSummary } from '#lib/api.ts';
	import { describePill } from '#lib/vocab.ts';

	interface Props {
		pill: PillSummary;
		searchedImprint: boolean;
	}

	let { pill, searchedImprint }: Props = $props();

	const match = $derived(matchLabel(pill.match_score, searchedImprint));
	const title = $derived(pillTitle(pill));
	const description = $derived(describePill(pill.shape, pill.colors, pill.imprint || null));
	const linkLabel = $derived(
		[
			[title, pill.strength].filter(Boolean).join(' '),
			`imprint ${pill.imprint || 'none'}`,
			pill.labeler,
			match
		]
			.filter(Boolean)
			.join(', ')
	);
</script>

<a class="result card" href={resolve('/pill/[id]', { id: String(pill.id) })} aria-label={linkLabel}>
	<div class="visuals">
		<div class="drawing">
			<PillGlyph
				shape={pill.shape}
				colors={pill.colors}
				sides={pill.imprint_sides}
				score={pill.score}
				form={pill.dosage_form}
				sizeMm={pill.size_mm}
				size={104}
				label={description}
			/>
		</div>
		<LabelPhoto
			src={pill.photo_url ?? pill.label_image_url}
			alt={`${pill.photo_url ? 'Photo' : 'Package label'} of ${title}`}
			width={148}
			height={104}
			caption={pill.photo_url ? 'Pill photo' : 'Label'}
		/>
	</div>

	<div class="body">
		<div class="tags">
			{#if match}<span class="tag" class:accent={pill.match_score >= 0.85}>{match}</span>{/if}
			{#if pill.dea_schedule}<span class="tag warn">Controlled {pill.dea_schedule}</span>{/if}
			{#if !pill.marketed}<span class="tag">Discontinued</span>{/if}
		</div>
		<h3>{title}</h3>
		<p class="strength">
			{#if pill.strength}{pill.strength}{/if}
			{#if pill.generic_name && pill.generic_name.toLowerCase() !== title.toLowerCase()}
				<span class="generic">· {pill.generic_name}</span>
			{/if}
		</p>
		<dl class="facts">
			<div>
				<dt>Imprint</dt>
				<dd class="mono">{pill.imprint || 'None'}</dd>
			</div>
			{#if pill.size_mm}
				<div>
					<dt>Size</dt>
					<dd>{pill.size_mm} mm</dd>
				</div>
			{/if}
		</dl>
		<p class="labeler">
			{pill.labeler ?? 'Unknown labeler'}
			{#if pill.group_size > 1}
				<span class="more">+{pill.group_size - 1} more</span>
			{/if}
		</p>
	</div>
</a>

<style>
	.result {
		display: flex;
		gap: 1rem;
		padding: 0.9rem;
		color: inherit;
		text-decoration: none;
		transition:
			box-shadow 0.15s,
			border-color 0.15s,
			transform 0.15s;
	}
	.result:hover {
		border-color: var(--line-strong);
		box-shadow: var(--shadow-lg);
		transform: translateY(-1px);
	}
	.visuals {
		display: flex;
		gap: 0.5rem;
		flex: none;
	}
	.drawing {
		display: grid;
		place-items: center;
		width: 104px;
		height: 104px;
		border-radius: var(--radius-sm);
		background: radial-gradient(circle at 50% 40%, var(--surface) 0%, var(--surface-2) 75%);
		border: 1px solid var(--line);
	}
	.body {
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		min-height: 1.25rem;
	}
	h3 {
		font-size: 1.02rem;
		overflow-wrap: anywhere;
	}
	.strength {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--ink-2);
	}
	.generic {
		font-weight: 400;
		color: var(--muted);
	}
	.facts {
		display: flex;
		gap: 1rem;
		margin: 0.15rem 0 0;
		font-size: 0.85rem;
	}
	.facts div {
		display: flex;
		gap: 0.35rem;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
		font-weight: 700;
	}
	.labeler {
		margin-top: auto;
		font-size: 0.8rem;
		color: var(--muted);
		overflow-wrap: anywhere;
	}
	.more {
		margin-left: 0.25rem;
		color: var(--accent);
		font-weight: 600;
	}
	@media (max-width: 560px) {
		.result {
			flex-direction: column;
		}
		.visuals :global(.photo) {
			flex: 1 1 auto;
			width: auto !important;
		}
	}
</style>
