<script lang="ts">
	import { SCORES } from '#lib/vocab.ts';

	interface Props {
		value: number | null;
		onchange: (value: number | null) => void;
	}

	let { value, onchange }: Props = $props();

	function lines(pieces: number): Array<[number, number, number, number]> {
		if (pieces === 2) return [[12, 3, 12, 21]];
		if (pieces === 3)
			return [
				[9, 3, 9, 21],
				[15, 3, 15, 21]
			];
		if (pieces === 4)
			return [
				[12, 3, 12, 21],
				[3, 12, 21, 12]
			];
		return [];
	}
</script>

<div class="segments" role="group" aria-label="Score lines">
	<button
		type="button"
		class:selected={value === null}
		aria-pressed={value === null}
		onclick={() => onchange(null)}>Any</button
	>
	{#each SCORES as option (option.value)}
		<button
			type="button"
			class:selected={value === option.value}
			aria-pressed={value === option.value}
			title={option.hint}
			onclick={() => onchange(value === option.value ? null : option.value)}
		>
			<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
				<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8" />
				{#each lines(option.value) as [x1, y1, x2, y2], i (i)}
					<line {x1} {y1} {x2} {y2} stroke="currentColor" stroke-width="1.8" />
				{/each}
			</svg>
			{option.label}
		</button>
	{/each}
</div>

<style>
	.segments {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}
	button {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 40px;
		padding: 0.35rem 0.75rem;
		border: 1.5px solid var(--line);
		border-radius: 999px;
		background: var(--surface);
		color: var(--ink-2);
		font-size: 0.85rem;
		font-weight: 600;
		cursor: pointer;
	}
	button:hover {
		border-color: var(--line-strong);
	}
	button.selected {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--ink);
	}
</style>
