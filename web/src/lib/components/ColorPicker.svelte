<script lang="ts">
	import { darken } from '#lib/color.ts';
	import { MAX_COLORS } from '#lib/api.ts';
	import { COLORS, type ColorKey } from '#lib/vocab.ts';

	interface Props {
		value: readonly ColorKey[];
		onchange: (value: ColorKey[]) => void;
	}

	let { value, onchange }: Props = $props();

	function toggle(key: ColorKey) {
		if (value.includes(key)) onchange(value.filter((c) => c !== key));
		else onchange([...value, key].slice(-MAX_COLORS));
	}
</script>

<div class="swatches" role="group" aria-label="Color">
	{#each COLORS as color (color.key)}
		{@const index = value.indexOf(color.key)}
		<button
			type="button"
			class="swatch"
			class:selected={index >= 0}
			aria-pressed={index >= 0}
			onclick={() => toggle(color.key)}
		>
			<span class="dot" style:background={color.hex} style:border-color={darken(color.hex, 0.22)}>
				{#if index >= 0 && value.length > 1}<span class="order">{index + 1}</span>{/if}
			</span>
			<span class="name">{color.label}</span>
		</button>
	{/each}
</div>

<style>
	.swatches {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
		gap: 0.35rem;
	}
	.swatch {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.3rem;
		padding: 0.45rem 0.2rem;
		border: 1.5px solid transparent;
		border-radius: var(--radius-sm);
		background: none;
		cursor: pointer;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--ink-2);
	}
	.swatch:hover {
		background: var(--surface-2);
	}
	.swatch.selected {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--ink);
	}
	.dot {
		position: relative;
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: 50%;
		border: 1.5px solid;
		box-shadow:
			inset -3px -4px 8px rgb(0 0 0 / 14%),
			inset 3px 3px 6px rgb(255 255 255 / 45%);
	}
	.order {
		display: grid;
		place-items: center;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: var(--accent);
		color: var(--accent-ink);
		font-size: 0.7rem;
		font-weight: 800;
	}
</style>
