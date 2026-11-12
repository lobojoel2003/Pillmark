<script lang="ts">
	import PillGlyph from './PillGlyph.svelte';
	import { COMMON_SHAPES, SHAPES, type ShapeKey } from '#lib/vocab.ts';

	interface Props {
		value: ShapeKey | null;
		colors: readonly string[];
		onchange: (value: ShapeKey | null) => void;
	}

	let { value, colors, onchange }: Props = $props();
	let expanded = $state(false);

	const showAll = $derived(expanded || (value !== null && !COMMON_SHAPES.includes(value)));
	const visible = $derived(showAll ? SHAPES : SHAPES.filter((s) => COMMON_SHAPES.includes(s.key)));
	const tint = $derived(colors.length ? colors : ['white']);
</script>

<div class="grid" role="group" aria-label="Shape">
	{#each visible as shape (shape.key)}
		<button
			type="button"
			class="option"
			class:selected={value === shape.key}
			aria-pressed={value === shape.key}
			title={shape.hint}
			onclick={() => onchange(value === shape.key ? null : shape.key)}
		>
			<PillGlyph shape={shape.key} colors={tint} size={46} shadow={false} label="" />
			<span>{shape.label}</span>
		</button>
	{/each}
</div>
{#if !showAll}
	<button type="button" class="more" onclick={() => (expanded = true)}>
		More shapes ({SHAPES.length - COMMON_SHAPES.length})
	</button>
{/if}

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
		gap: 0.5rem;
	}
	.option {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.2rem;
		padding: 0.55rem 0.25rem 0.45rem;
		border: 1.5px solid var(--line);
		border-radius: var(--radius-sm);
		background: var(--surface);
		cursor: pointer;
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--ink-2);
		transition:
			border-color 0.15s,
			background 0.15s,
			transform 0.1s;
	}
	.option:hover {
		border-color: var(--line-strong);
	}
	.option:active {
		transform: scale(0.97);
	}
	.option.selected {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--ink);
	}
	.more {
		margin-top: 0.6rem;
		padding: 0;
		border: 0;
		background: none;
		color: var(--accent);
		font-weight: 600;
		font-size: 0.9rem;
		cursor: pointer;
	}
</style>
