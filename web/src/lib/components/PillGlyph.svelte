<!--
	Draws a pill from its attributes: shape, one or two colors, score lines and imprint.
	Two-piece hard capsules get a cap and a body with the imprint printed on each half.
-->
<script lang="ts">
	import { darken, isDark, lighten } from '#lib/color.ts';
	import { fitFont, isTwoPiece, outlineFor, scoreLines, sizeScale } from '#lib/geometry.ts';
	import { colorOf, describePill } from '#lib/vocab.ts';

	interface Props {
		shape?: string | null;
		colors?: readonly string[];
		imprint?: string | null;
		sides?: readonly string[] | null;
		score?: number | null;
		form?: string | null;
		sizeMm?: number | null;
		/** Rendered width and height in pixels. */
		size?: number;
		/** Draw an empty, dashed placeholder (nothing chosen yet). */
		muted?: boolean;
		shadow?: boolean;
		label?: string;
	}

	let {
		shape = null,
		colors = [],
		imprint = null,
		sides = null,
		score = null,
		form = null,
		sizeMm = null,
		size = 160,
		muted = false,
		shadow = true,
		label
	}: Props = $props();

	const uid = $props.id();

	const outline = $derived(outlineFor(shape));
	const hexes = $derived(colors.map((c) => colorOf(c)?.hex).filter((h): h is string => Boolean(h)));
	const base = $derived(hexes[0] ?? (muted ? '#EEEAE1' : '#F4F1EA'));
	const second = $derived(hexes[1] ?? null);
	const twoPiece = $derived(isTwoPiece(shape, form, colors));
	const scale = $derived(sizeScale(sizeMm));
	const rim = $derived(darken(base, isDark(base) ? 0.35 : 0.2));
	const grooves = $derived(twoPiece ? [] : scoreLines(outline, score));

	const sideTexts = $derived.by(() => {
		const list = (sides ?? []).map((s) => s.trim()).filter(Boolean);
		if (list.length) return list;
		const text = imprint?.trim();
		return text ? [text] : [];
	});

	// Tablets: up to three lines stacked on the face. Capsules: one side per half.
	const lines = $derived.by(() => {
		if (twoPiece || !sideTexts.length) return [];
		if (sideTexts.length <= 3) return sideTexts;
		return [sideTexts.join(' ')];
	});

	const fontSize = $derived.by(() => {
		if (!lines.length) return 0;
		const byWidth = Math.min(...lines.map((l) => fitFont(l, outline.textWidth, 44)));
		const byHeight = (outline.halfHeight * 1.25) / lines.length;
		return Math.min(byWidth, byHeight, 44);
	});

	const capsuleHalves = $derived.by(() => {
		if (!twoPiece || !sideTexts.length) return [];
		const [first, ...rest] = sideTexts;
		const halves = [{ text: first, x: 57, color: base }];
		if (rest.length) halves.push({ text: rest.join(' '), x: 143, color: second ?? base });
		return halves.map((h) => ({ ...h, size: Math.min(fitFont(h.text, 70, 28), 28) }));
	});

	function inkFor(hex: string): string {
		return isDark(hex) ? lighten(hex, 0.75) : '#2A2622';
	}

	function engrave(hex: string): string {
		return isDark(hex) ? lighten(hex, 0.35) : darken(hex, 0.38);
	}

	const textBaseY = $derived(outline.textY - ((lines.length - 1) * fontSize * 1.05) / 2);
	const description = $derived(
		label ?? describePill(shape, colors, sideTexts.length ? sideTexts.join(' ') : null)
	);
</script>

<svg
	class="pill"
	viewBox="0 0 200 200"
	width={size}
	height={size}
	role="img"
	aria-label={description}
>
	<defs>
		<clipPath id="{uid}-clip"><path d={outline.d} /></clipPath>
		<radialGradient id="{uid}-shine" cx="34%" cy="26%" r="78%">
			<stop offset="0" stop-color="#fff" stop-opacity={muted ? 0.2 : 0.7} />
			<stop offset="0.45" stop-color="#fff" stop-opacity="0.08" />
			<stop offset="1" stop-color="#fff" stop-opacity="0" />
		</radialGradient>
		<linearGradient id="{uid}-shade" x1="0" y1="0" x2="0" y2="1">
			<stop offset="0.45" stop-color="#000" stop-opacity="0" />
			<stop offset="1" stop-color="#000" stop-opacity={muted ? 0.04 : 0.16} />
		</linearGradient>
		<filter id="{uid}-blur" x="-20%" y="-50%" width="140%" height="200%">
			<feGaussianBlur stdDeviation="5" />
		</filter>
	</defs>

	<g transform="translate(100 100) scale({scale}) translate(-100 -100)">
		{#if shadow && !muted}
			<ellipse
				cx="100"
				cy={100 + outline.halfHeight + 8}
				rx={outline.halfWidth * 0.78}
				ry="7"
				fill="#000"
				opacity="0.14"
				filter="url(#{uid}-blur)"
			/>
		{/if}

		<g clip-path="url(#{uid}-clip)">
			<rect x="0" y="0" width="200" height="200" fill={base} />
			{#if second}
				<rect x="100" y="0" width="100" height="200" fill={second} />
			{/if}

			{#if twoPiece}
				<!-- The cap overlaps the body slightly; draw the seam and its lip. -->
				<line
					x1="100"
					y1="0"
					x2="100"
					y2="200"
					stroke={darken(second ?? base, 0.25)}
					stroke-width="2.5"
				/>
				<line
					x1="96"
					y1="0"
					x2="96"
					y2="200"
					stroke="#fff"
					stroke-opacity="0.35"
					stroke-width="1.5"
				/>
			{/if}

			{#each grooves as [x1, y1, x2, y2], i (i)}
				<line
					{x1}
					{y1}
					{x2}
					{y2}
					stroke="#fff"
					stroke-opacity="0.55"
					stroke-width="5"
					transform="translate(1.6 1.6)"
				/>
				<line {x1} {y1} {x2} {y2} stroke={darken(base, 0.24)} stroke-width="4" />
			{/each}

			{#if lines.length}
				<g class="imprint" font-size={fontSize} text-anchor="middle" dominant-baseline="central">
					{#each lines as line, i (i)}
						<text
							x="100"
							y={textBaseY + i * fontSize * 1.05 + 1.4}
							fill="#fff"
							fill-opacity={isDark(base) ? 0.12 : 0.6}>{line}</text
						>
						<text x="100" y={textBaseY + i * fontSize * 1.05} fill={engrave(base)}>{line}</text>
					{/each}
				</g>
			{/if}

			{#each capsuleHalves as half, i (i)}
				<text
					class="imprint printed"
					x={half.x}
					y="100"
					font-size={half.size}
					text-anchor="middle"
					dominant-baseline="central"
					fill={inkFor(half.color)}>{half.text}</text
				>
			{/each}

			<rect x="0" y="0" width="200" height="200" fill="url(#{uid}-shade)" />
			<rect x="0" y="0" width="200" height="200" fill="url(#{uid}-shine)" />
		</g>

		<path
			d={outline.d}
			fill="none"
			stroke={muted ? '#B9B2A4' : rim}
			stroke-width={muted ? 2.5 : 2.2}
			stroke-dasharray={muted ? '7 6' : undefined}
			stroke-linejoin="round"
		/>
	</g>
</svg>

<style>
	.pill {
		display: block;
		overflow: visible;
	}
	.imprint {
		font-family:
			ui-sans-serif,
			system-ui,
			-apple-system,
			'Segoe UI',
			Roboto,
			'Helvetica Neue',
			Arial,
			sans-serif;
		font-weight: 800;
		letter-spacing: 0.04em;
	}
	.printed {
		font-weight: 700;
		letter-spacing: 0.02em;
	}
</style>
