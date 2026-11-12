<script lang="ts">
	let { compact = false }: { compact?: boolean } = $props();
</script>

<aside class="safety" class:compact aria-label="Safety">
	<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
		<path
			d="M12 3 2.5 20h19L12 3Z M12 10v4.5 M12 17.2v.3"
			fill="none"
			stroke="currentColor"
			stroke-width="1.9"
			stroke-linejoin="round"
			stroke-linecap="round"
		/>
	</svg>
	<p>
		<strong>Swallowed by someone it wasn't prescribed for?</strong>
		Call Poison Control at <a href="tel:18002221222">1-800-222-1222</a> (US) or your local emergency
		number now; don't wait for a match.
		{#if !compact}
			Pillmark is not medical advice; confirm any pill with a pharmacist.
		{/if}
	</p>
</aside>

<style>
	.safety {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
		padding: 0.9rem 1rem;
		border-radius: var(--radius-sm);
		background: var(--danger-soft);
		color: var(--ink-2);
		font-size: 0.9rem;
	}
	.safety svg {
		flex: none;
		color: var(--danger);
		margin-top: 0.1rem;
	}
	.safety strong {
		color: var(--ink);
	}
	.safety a {
		color: var(--danger);
		font-weight: 700;
		white-space: nowrap;
	}
	.compact {
		font-size: 0.85rem;
		padding: 0.7rem 0.9rem;
	}
</style>
