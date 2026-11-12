<script lang="ts">
	import { resolve } from '$app/paths';
	import SafetyNotice from '#lib/components/SafetyNotice.svelte';
</script>

<svelte:head>
	<title>About · Pillmark</title>
	<meta
		name="description"
		content="Why Pillmark exists, where its data comes from and how pill matching works."
	/>
</svelte:head>

<div class="container page">
	<p class="eyebrow">About</p>
	<h1>A free, open pill identifier</h1>

	<div class="prose">
		<p class="lead">
			A loose pill on the floor, a mixed-up pill organizer, a child who may have swallowed
			something: people need to identify a pill from its imprint, color and shape, fast.
		</p>

		<SafetyNotice />

		<h2>Why it exists</h2>
		<p>
			The U.S. National Library of Medicine retired Pillbox, its free pill identifier, on January
			29, 2021, including its site, data, images and APIs. NLM points people to MedlinePlus and
			DailyMed, but says
			<a
				href="https://www.nlm.nih.gov/pubs/techbull/ja20/ja20_pillbox_discontinue.html"
				rel="external">"these resources do not provide pill identification"</a
			>. It
			<a
				href="https://www.route-fifty.com/digital-government/2021/05/nlm-pillbox-put-out-to-pasture/316051/"
				rel="external">has no plans to replace Pillbox</a
			>. Pillbox's final data is still downloadable but frozen, and NLM says it
			<a href="https://beautifulpublicdata.com/the-pillbox-database" rel="external"
				>"should not be used for pill identification"</a
			>.
		</p>
		<p>
			The free identifiers left are closed and ad-supported, with no public API. Pillmark is open
			source, has a free public API, and refreshes its data every night.
		</p>

		<h2>Where the data comes from</h2>
		<p>
			Every drug label sent to the FDA uses Structured Product Labeling (SPL). For solid oral
			products, a label records each pill's imprint, color, shape, size and score lines, and
			DailyMed publishes all labels, with updates every day. Pillmark imports those daily files each
			night, keeps the newest version of every label, and shows the label's package photo next to a
			drawing of the pill made from the recorded description.
		</p>

		<h2>How matching works</h2>
		<ul>
			<li>
				Imprints match however they're typed: <span class="mono">IP 204</span>,
				<span class="mono">ip204</span> and <span class="mono">204 IP</span> all find the same pill.
			</li>
			<li>
				Look-alike characters are tolerated (<span class="mono">0</span> and
				<span class="mono">O</span>, <span class="mono">1</span> and <span class="mono">I</span>),
				and one wrong character still finds a close match, ranked lower.
			</li>
			<li>
				Repackagers often sell the same pill under their own label. Pillmark groups them into one
				result and lists the others on the pill's page.
			</li>
		</ul>

		<h2>Limits</h2>
		<p>
			Pillmark only knows what manufacturers put in their labels. Imprints are sometimes missing or
			written inconsistently, colors are named by the manufacturer, and most labels have a photo of
			the package rather than of the pill. A match is a strong hint, not a confirmation. Ask a
			pharmacist before taking or giving any medicine you can't identify for sure.
		</p>

		<h2>Open source</h2>
		<p>
			Pillmark is Apache-2.0 licensed. The importer, database schema, API and this site are on
			<a href="https://github.com/lobojoel2003/Pillmark" rel="external">GitHub</a>. The data is
			public: build on it with the <a href={resolve('/developers')}>free API</a>.
		</p>
	</div>
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
		margin: 0.35rem 0 1.25rem;
		font-size: clamp(2rem, 4vw, 2.75rem);
	}
	.lead {
		font-size: 1.15rem;
		color: var(--ink);
		margin-bottom: 1.25rem;
	}
</style>
