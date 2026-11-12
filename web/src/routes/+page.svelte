<script lang="ts">
	import { untrack } from 'svelte';
	import { afterNavigate, goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { navigating, page } from '$app/state';
	import ColorPicker from '#lib/components/ColorPicker.svelte';
	import PillGlyph from '#lib/components/PillGlyph.svelte';
	import ResultCard from '#lib/components/ResultCard.svelte';
	import SafetyNotice from '#lib/components/SafetyNotice.svelte';
	import ScorePicker from '#lib/components/ScorePicker.svelte';
	import ShapePicker from '#lib/components/ShapePicker.svelte';
	import SizePicker from '#lib/components/SizePicker.svelte';
	import {
		criteriaToParams,
		emptyCriteria,
		hasCriteria,
		searchPills,
		type Criteria,
		type PillSummary
	} from '#lib/api.ts';
	import { describePill } from '#lib/vocab.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const clone = (c: Criteria): Criteria => ({ ...c, colors: [...c.colors] });

	// Local copy so the drawing reacts to every keystroke; the URL follows shortly after.
	let criteria: Criteria = $state(untrack(() => clone(data.criteria)));
	let more: PillSummary[] = $state([]);
	let loadingMore = $state(false);
	let moreError: string | null = $state(null);
	let resultsInView = $state(false);
	let resultsSection: HTMLElement | undefined = $state();
	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		if (!resultsSection) return;
		const observer = new IntersectionObserver(([entry]) => (resultsInView = entry.isIntersecting));
		observer.observe(resultsSection);
		return () => observer.disconnect();
	});

	afterNavigate(({ type }) => {
		more = [];
		moreError = null;
		// Back/forward and links change the URL under us: follow it.
		if (type !== 'goto') criteria = clone(data.criteria);
	});

	function update(patch: Partial<Criteria>, delay = 0) {
		criteria = { ...criteria, ...patch };
		clearTimeout(timer);
		timer = setTimeout(() => {
			const search = criteriaToParams(criteria).toString();
			if ((search ? `?${search}` : '') !== page.url.search) {
				goto(search ? resolve(`/?${search}`) : resolve('/'), { replace: true, reset: false });
			}
		}, delay);
	}

	function reset() {
		update(emptyCriteria());
	}

	function example(patch: Partial<Criteria>) {
		update({ ...emptyCriteria(), ...patch });
	}

	async function loadMore() {
		if (!data.search) return;
		loadingMore = true;
		moreError = null;
		try {
			const next = await searchPills(
				fetch,
				data.criteria,
				data.search.results.length + more.length
			);
			more = [...more, ...next.results];
		} catch {
			moreError = 'Could not load more results. Try again.';
		} finally {
			loadingMore = false;
		}
	}

	const active = $derived(hasCriteria(criteria));
	const results = $derived([...(data.search?.results ?? []), ...more]);
	const total = $derived(data.search?.total ?? 0);
	const busy = $derived(navigating.to !== null && navigating.to?.url.pathname === '/');
	const searchedImprint = $derived(Boolean(data.criteria.imprint.trim()));
	const drawn = $derived(Boolean(criteria.shape || criteria.colors.length || criteria.imprint));
	const caption = $derived(
		drawn
			? describePill(criteria.shape, criteria.colors, criteria.imprint.trim() || null)
			: 'Tap a shape and a color to draw the pill'
	);
	const title = 'Pillmark: identify a pill by imprint, color and shape';
</script>

<svelte:head>
	<title>{title}</title>
	<meta property="og:title" content={title} />
	<meta
		property="og:description"
		content="Draw the pill you found and match it against FDA drug labels. Free and open."
	/>
</svelte:head>

<div class="container layout">
	<section class="panel card" aria-labelledby="describe">
		<div class="stage" aria-live="polite">
			<PillGlyph
				shape={criteria.shape}
				colors={criteria.colors}
				imprint={criteria.imprint}
				score={criteria.score}
				sizeMm={criteria.size ?? 16}
				size={190}
				muted={!drawn}
				label={caption}
			/>
			<p class="caption">{caption}</p>
		</div>

		<h1 id="describe" class="visually-hidden">Describe the pill</h1>

		<div class="field">
			<label class="label" for="imprint">What's printed on it?</label>
			<div class="imprint-row">
				<input
					id="imprint"
					class="imprint mono"
					type="search"
					inputmode="text"
					autocomplete="off"
					autocapitalize="characters"
					spellcheck="false"
					maxlength="64"
					placeholder="e.g. M 367"
					value={criteria.imprint}
					disabled={criteria.noImprint}
					oninput={(e) => update({ imprint: e.currentTarget.value, noImprint: false }, 300)}
				/>
			</div>
			<p class="hint">Letters, numbers or both, from any side, in any order.</p>
			<label class="check">
				<input
					type="checkbox"
					checked={criteria.noImprint}
					onchange={(e) => update({ noImprint: e.currentTarget.checked, imprint: '' })}
				/>
				It has no imprint
			</label>
		</div>

		<div class="field">
			<span class="label" id="shape-label">Shape</span>
			<ShapePicker
				value={criteria.shape}
				colors={criteria.colors}
				onchange={(shape) => update({ shape })}
			/>
		</div>

		<div class="field">
			<span class="label">Color <span class="soft">· pick two for two-tone pills</span></span>
			<ColorPicker value={criteria.colors} onchange={(colors) => update({ colors })} />
		</div>

		<div class="field">
			<span class="label">Score lines</span>
			<ScorePicker value={criteria.score} onchange={(score) => update({ score })} />
		</div>

		<div class="field">
			<span class="label">Size</span>
			<SizePicker value={criteria.size} onchange={(size) => update({ size }, 250)} />
		</div>

		<details class="field" open={Boolean(criteria.name)}>
			<summary class="label">Know the name or maker?</summary>
			<input
				class="name"
				type="search"
				placeholder="e.g. lisinopril, Teva"
				autocomplete="off"
				maxlength="100"
				value={criteria.name}
				oninput={(e) => update({ name: e.currentTarget.value }, 350)}
				aria-label="Drug, brand or maker name"
			/>
		</details>

		{#if active}
			<button type="button" class="button ghost reset" onclick={reset}>Start over</button>
		{/if}
	</section>

	{#if data.search && total > 0 && !resultsInView}
		<a class="jump button primary" href="#results-title">
			See {total.toLocaleString('en-US')}
			{total === 1 ? 'match' : 'matches'} ↓
		</a>
	{/if}

	<section
		class="results"
		aria-labelledby="results-title"
		aria-busy={busy}
		bind:this={resultsSection}
	>
		{#if !data.search && !data.error}
			<div class="intro">
				<p class="eyebrow">Open pill identifier</p>
				<h2 id="results-title">Found a pill? Draw it, and we'll find it.</h2>
				<p class="lead">
					Pillmark matches the imprint, shape and color you see against the FDA drug labels
					published on DailyMed, and shows each label's photo next to a drawing of the pill.
				</p>
				<ol class="steps">
					<li>
						<strong>Read the imprint.</strong> Letters and numbers pressed or printed on the pill narrow
						things down fastest.
					</li>
					<li><strong>Tap the shape</strong>, so nobody needs to know the word "oblong".</li>
					<li><strong>Tap the color</strong>, or two colors for a two-tone capsule.</li>
				</ol>
				<div class="examples">
					<span>Try</span>
					<button
						type="button"
						onclick={() => example({ imprint: 'LUPIN 10', shape: 'round', colors: ['pink'] })}
						>LUPIN 10 · pink round</button
					>
					<button
						type="button"
						onclick={() => example({ imprint: 'SG 179', shape: 'capsule', colors: ['white'] })}
						>SG 179 · white oblong</button
					>
					<button
						type="button"
						onclick={() => example({ shape: 'capsule', colors: ['yellow', 'white'] })}
						>yellow and white capsule</button
					>
				</div>
				<SafetyNotice />
			</div>
		{:else}
			<header class="results-head" id="results-head">
				<h2 id="results-title">
					{#if data.error}
						Search unavailable
					{:else if total === 0}
						No matches
					{:else}
						{total.toLocaleString('en-US')}
						{total === 1 ? 'match' : 'matches'}
					{/if}
				</h2>
				{#if busy}<span class="spinner" role="status" aria-label="Searching"></span>{/if}
			</header>

			<SafetyNotice compact />

			{#if data.error}
				<p class="message">{data.error}</p>
			{:else if total === 0}
				<div class="message">
					<p><strong>Nothing matches all of that.</strong> A few things to try:</p>
					<ul>
						<li>Check look-alike characters: 0 and O, 1 and I or L, 5 and S, 8 and B.</li>
						<li>Remove the color: lighting changes how colors look.</li>
						<li>Search the imprint alone, or only the clearest part of it.</li>
					</ul>
				</div>
			{:else}
				<ul class="list" class:dim={busy}>
					{#each results as pill (pill.id)}
						<li><ResultCard {pill} {searchedImprint} /></li>
					{/each}
				</ul>
				{#if results.length < total}
					<div class="more">
						<button type="button" class="button" onclick={loadMore} disabled={loadingMore}>
							{loadingMore ? 'Loading…' : `Show more (${total - results.length} left)`}
						</button>
						{#if moreError}<p class="hint">{moreError}</p>{/if}
					</div>
				{/if}
			{/if}
		{/if}
	</section>
</div>

<style>
	.layout {
		display: grid;
		grid-template-columns: minmax(330px, 410px) minmax(0, 1fr);
		gap: 2rem;
		align-items: start;
		padding-top: 1.5rem;
	}
	.panel {
		position: sticky;
		top: 80px;
		max-height: calc(100vh - 96px);
		overflow: auto;
		padding: 1.1rem 1.2rem 1.4rem;
		scrollbar-width: thin;
	}
	.stage {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		margin: -0.2rem -0.3rem 0.4rem;
		padding: 1rem 0 0.9rem;
		border-radius: 12px;
		background:
			radial-gradient(circle at 50% 42%, var(--surface) 0%, var(--surface-2) 72%), var(--surface-2);
	}
	.caption {
		min-height: 1.4em;
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--ink-2);
		text-align: center;
		padding-inline: 1rem;
	}
	.field {
		margin-top: 1.25rem;
	}
	.label {
		display: block;
		margin-bottom: 0.5rem;
		font-weight: 700;
		font-size: 0.95rem;
	}
	.soft {
		font-weight: 500;
		color: var(--muted);
		font-size: 0.85rem;
	}
	summary.label {
		cursor: pointer;
	}
	.imprint,
	.name {
		width: 100%;
		min-height: 48px;
		padding: 0.6rem 0.9rem;
		border: 1.5px solid var(--line-strong);
		border-radius: 12px;
		background: var(--surface);
	}
	.imprint {
		font-size: 1.25rem;
		font-weight: 700;
		text-transform: uppercase;
	}
	.imprint::placeholder {
		text-transform: none;
		font-weight: 500;
		color: var(--muted);
	}
	.imprint:focus,
	.name:focus {
		border-color: var(--accent);
		outline: none;
		box-shadow: 0 0 0 3px var(--accent-soft);
	}
	.imprint:disabled {
		opacity: 0.5;
	}
	.hint {
		margin-top: 0.4rem;
		font-size: 0.85rem;
		color: var(--muted);
	}
	.check {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		margin-top: 0.5rem;
		font-size: 0.9rem;
		cursor: pointer;
	}
	.check input {
		width: 18px;
		height: 18px;
		accent-color: var(--accent);
	}
	.reset {
		margin-top: 1.25rem;
		width: 100%;
		color: var(--accent);
	}
	.results {
		min-width: 0;
	}
	.results :global(h2) {
		scroll-margin-top: 88px;
	}
	.intro {
		display: flex;
		flex-direction: column;
		gap: 1.1rem;
		padding-top: 1.5rem;
		max-width: 640px;
	}
	.eyebrow {
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--accent);
	}
	.intro h2 {
		font-size: clamp(2rem, 4vw, 2.9rem);
		letter-spacing: -0.035em;
	}
	.lead {
		font-size: 1.1rem;
		color: var(--ink-2);
	}
	.steps {
		display: grid;
		gap: 0.6rem;
		margin: 0;
		padding: 0;
		list-style: none;
		counter-reset: step;
	}
	.steps li {
		position: relative;
		padding-left: 2.4rem;
		color: var(--ink-2);
	}
	.steps li::before {
		counter-increment: step;
		content: counter(step);
		position: absolute;
		left: 0;
		top: -0.05rem;
		display: grid;
		place-items: center;
		width: 1.7rem;
		height: 1.7rem;
		border-radius: 50%;
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 800;
		font-size: 0.85rem;
	}
	.steps strong {
		color: var(--ink);
	}
	.examples {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		color: var(--muted);
	}
	.examples button {
		padding: 0.4rem 0.8rem;
		border: 1px solid var(--line-strong);
		border-radius: 999px;
		background: var(--surface);
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.examples button:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.results-head {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		margin: 0.4rem 0 0.9rem;
	}
	.results-head h2 {
		font-size: 1.5rem;
	}
	.spinner {
		width: 18px;
		height: 18px;
		border: 2.5px solid var(--line-strong);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 430px), 1fr));
		gap: 0.9rem;
		margin: 1rem 0 0;
		padding: 0;
		list-style: none;
		transition: opacity 0.2s;
	}
	.list.dim {
		opacity: 0.55;
	}
	.message {
		margin-top: 1rem;
		padding: 1.1rem 1.2rem;
		border: 1px dashed var(--line-strong);
		border-radius: var(--radius);
		color: var(--ink-2);
	}
	.message ul {
		margin: 0.6rem 0 0;
		padding-left: 1.2rem;
	}
	.more {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1.4rem;
	}
	.jump {
		display: none;
	}
	@media (max-width: 960px) {
		.layout {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}
		.jump {
			display: inline-flex;
			position: fixed;
			left: 50%;
			bottom: max(1rem, env(safe-area-inset-bottom));
			z-index: 4;
			transform: translateX(-50%);
			box-shadow: var(--shadow-lg);
		}
		.panel {
			position: static;
			max-height: none;
		}
		.intro {
			padding-top: 0;
		}
	}
</style>
