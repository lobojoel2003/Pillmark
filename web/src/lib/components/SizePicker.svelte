<script lang="ts">
	interface Props {
		value: number | null;
		onchange: (value: number | null) => void;
	}

	let { value, onchange }: Props = $props();
	const MIN = 3;
	const MAX = 25;
</script>

<div class="size">
	{#if value === null}
		<button type="button" class="set" onclick={() => onchange(10)}>
			<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
				<path
					d="M3 8h18v8H3z M7 8v3 M11 8v4 M15 8v3 M19 8v4"
					fill="none"
					stroke="currentColor"
					stroke-width="1.6"
				/>
			</svg>
			I measured it
		</button>
		<span class="hint">Optional. Use a ruler across the longest side.</span>
	{:else}
		<label class="slider">
			<span class="visually-hidden">Longest side in millimetres</span>
			<input
				type="range"
				min={MIN}
				max={MAX}
				step="1"
				{value}
				oninput={(e) => onchange(Number(e.currentTarget.value))}
			/>
		</label>
		<output class="value">{value} mm <span class="tolerance">± 1</span></output>
		<button type="button" class="clear" onclick={() => onchange(null)}>Clear</button>
	{/if}
</div>

<style>
	.size {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.6rem 0.9rem;
	}
	.set,
	.clear {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		min-height: 40px;
		padding: 0.35rem 0.85rem;
		border: 1.5px solid var(--line);
		border-radius: 999px;
		background: var(--surface);
		font-size: 0.85rem;
		font-weight: 600;
		cursor: pointer;
	}
	.clear {
		border-color: transparent;
		color: var(--accent);
		padding-inline: 0.4rem;
	}
	.hint {
		font-size: 0.85rem;
		color: var(--muted);
	}
	.slider {
		flex: 1 1 160px;
	}
	input[type='range'] {
		width: 100%;
		accent-color: var(--accent);
	}
	.value {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.tolerance {
		color: var(--muted);
		font-weight: 500;
		font-size: 0.85rem;
	}
</style>
