// Pill outlines, drawn in a 200 × 200 box centred on (100, 100).

import type { ShapeKey } from './vocab';

export interface Outline {
	/** SVG path for the pill body. */
	d: string;
	/** Width available for imprint text on the face. */
	textWidth: number;
	/** Vertical centre for imprint text (shapes like a half circle sit low). */
	textY: number;
	/** Half extent of the body along x and y, used to place score lines. */
	halfWidth: number;
	halfHeight: number;
}

type Point = [number, number];

const C = 100;

function round(n: number): number {
	return Math.round(n * 100) / 100;
}

function fmt([x, y]: Point): string {
	return `${round(x)} ${round(y)}`;
}

/** A closed polygon with every corner rounded by ``radius``. */
export function roundedPolygon(points: readonly Point[], radius: number): string {
	const n = points.length;
	let d = '';
	for (let i = 0; i < n; i++) {
		const prev = points[(i - 1 + n) % n];
		const here = points[i];
		const next = points[(i + 1) % n];
		const toPrev: Point = [prev[0] - here[0], prev[1] - here[1]];
		const toNext: Point = [next[0] - here[0], next[1] - here[1]];
		const lenPrev = Math.hypot(...toPrev);
		const lenNext = Math.hypot(...toNext);
		const r = Math.min(radius, lenPrev / 2, lenNext / 2);
		const a: Point = [here[0] + (toPrev[0] / lenPrev) * r, here[1] + (toPrev[1] / lenPrev) * r];
		const b: Point = [here[0] + (toNext[0] / lenNext) * r, here[1] + (toNext[1] / lenNext) * r];
		d += `${i === 0 ? 'M' : 'L'}${fmt(a)} Q${fmt(here)} ${fmt(b)} `;
	}
	return d + 'Z';
}

/** Points of a regular polygon with a flat bottom edge, centred in the box. */
export function regularPolygon(sides: number, radius: number): Point[] {
	const start = Math.PI / 2 + Math.PI / sides;
	const points: Point[] = Array.from({ length: sides }, (_, k) => {
		const angle = start + (2 * Math.PI * k) / sides;
		return [radius * Math.cos(angle), radius * Math.sin(angle)];
	});
	return centre(points);
}

function centre(points: Point[]): Point[] {
	const xs = points.map((p) => p[0]);
	const ys = points.map((p) => p[1]);
	const dx = C - (Math.min(...xs) + Math.max(...xs)) / 2;
	const dy = C - (Math.min(...ys) + Math.max(...ys)) / 2;
	return points.map(([x, y]) => [x + dx, y + dy]);
}

function extent(points: Point[]): { halfWidth: number; halfHeight: number } {
	const xs = points.map((p) => p[0]);
	const ys = points.map((p) => p[1]);
	return {
		halfWidth: (Math.max(...xs) - Math.min(...xs)) / 2,
		halfHeight: (Math.max(...ys) - Math.min(...ys)) / 2
	};
}

function polygon(points: Point[], radius: number, textWidth: number, textY = C): Outline {
	return { d: roundedPolygon(points, radius), textWidth, textY, ...extent(points) };
}

function gear(teeth: number, outer: number, inner: number): Point[] {
	const step = (2 * Math.PI) / teeth;
	const points: Point[] = [];
	for (let k = 0; k < teeth; k++) {
		const t = k * step - Math.PI / 2;
		for (const [r, offset] of [
			[inner, -0.34],
			[outer, -0.17],
			[outer, 0.17],
			[inner, 0.34]
		] as const) {
			points.push([C + r * Math.cos(t + offset * step), C + r * Math.sin(t + offset * step)]);
		}
	}
	return points;
}

function rect(x: number, y: number, w: number, h: number, r: number): string {
	return roundedPolygon(
		[
			[x, y],
			[x + w, y],
			[x + w, y + h],
			[x, y + h]
		],
		r
	);
}

const OUTLINES: Record<ShapeKey, () => Outline> = {
	round: () => ({
		d: 'M20 100 A80 80 0 1 0 180 100 A80 80 0 1 0 20 100 Z',
		textWidth: 120,
		textY: C,
		halfWidth: 80,
		halfHeight: 80
	}),
	oval: () => ({
		d: 'M12 100 A88 62 0 1 0 188 100 A88 62 0 1 0 12 100 Z',
		textWidth: 128,
		textY: C,
		halfWidth: 88,
		halfHeight: 62
	}),
	capsule: () => ({
		d: 'M54 58 H146 A42 42 0 0 1 146 142 H54 A42 42 0 0 1 54 58 Z',
		textWidth: 140,
		textY: C,
		halfWidth: 88,
		halfHeight: 42
	}),
	rectangle: () => ({
		d: rect(16, 50, 168, 100, 18),
		textWidth: 136,
		textY: C,
		halfWidth: 84,
		halfHeight: 50
	}),
	square: () => ({
		d: rect(28, 28, 144, 144, 22),
		textWidth: 112,
		textY: C,
		halfWidth: 72,
		halfHeight: 72
	}),
	triangle: () => polygon(regularPolygon(3, 98), 18, 84, 116),
	diamond: () =>
		polygon(
			[
				[100, 12],
				[188, 100],
				[100, 188],
				[12, 100]
			],
			16,
			96
		),
	pentagon: () => polygon(regularPolygon(5, 90), 12, 104, 106),
	hexagon: () => polygon(regularPolygon(6, 88), 10, 120),
	heptagon: () => polygon(regularPolygon(7, 88), 9, 116, 103),
	octagon: () => polygon(regularPolygon(8, 88), 8, 124),
	'semi-circle': () => ({
		d: 'M14 143 A86 86 0 0 1 186 143 Z',
		textWidth: 112,
		textY: 116,
		halfWidth: 86,
		halfHeight: 43
	}),
	tear: () => ({
		d: 'M100 10 C128 50 170 84 170 118 A70 70 0 0 1 30 118 C30 84 72 50 100 10 Z',
		textWidth: 100,
		textY: 126,
		halfWidth: 70,
		halfHeight: 89
	}),
	trapezoid: () =>
		polygon(
			[
				[52, 52],
				[148, 52],
				[186, 148],
				[14, 148]
			],
			14,
			110
		),
	bullet: () => ({
		d: 'M26 58 H140 A42 42 0 0 1 140 142 H26 Q18 142 18 134 V66 Q18 58 26 58 Z',
		textWidth: 128,
		textY: C,
		halfWidth: 82,
		halfHeight: 42
	}),
	clover: () => ({
		d: 'M58 58 A42 42 0 0 1 142 58 A42 42 0 0 1 142 142 A42 42 0 0 1 58 142 A42 42 0 0 1 58 58 Z',
		textWidth: 104,
		textY: C,
		halfWidth: 84,
		halfHeight: 84
	}),
	gear: () => ({
		d: roundedPolygon(gear(12, 88, 74), 3),
		textWidth: 112,
		textY: C,
		halfWidth: 88,
		halfHeight: 88
	}),
	'double-circle': () => ({
		d: 'M100 51.6 A58 58 0 1 0 100 148.4 A58 58 0 1 0 100 51.6 Z',
		textWidth: 132,
		textY: C,
		halfWidth: 90,
		halfHeight: 58
	}),
	freeform: () => ({
		d: 'M100 18 C150 14 186 52 178 98 C172 140 140 182 96 178 C52 176 16 146 22 100 C28 58 54 22 100 18 Z',
		textWidth: 112,
		textY: C,
		halfWidth: 82,
		halfHeight: 80
	})
};

const cache = new Map<string, Outline>();

/** The outline for a shape; unknown or missing shapes draw as round. */
export function outlineFor(shape: string | null | undefined): Outline {
	const key = (shape && shape in OUTLINES ? shape : 'round') as ShapeKey;
	let outline = cache.get(key);
	if (!outline) {
		outline = OUTLINES[key]();
		cache.set(key, outline);
	}
	return outline;
}

/** Score grooves: lines across the body, clipped to it by the caller. */
export function scoreLines(
	outline: Outline,
	pieces: number | null | undefined
): Array<[number, number, number, number]> {
	if (!pieces || pieces < 2) return [];
	const top = C - outline.halfHeight - 4;
	const bottom = C + outline.halfHeight + 4;
	if (pieces === 2) return [[C, top, C, bottom]];
	if (pieces === 3) {
		const third = (outline.halfWidth * 2) / 3;
		return [
			[C - third / 2, top, C - third / 2, bottom],
			[C + third / 2, top, C + third / 2, bottom]
		];
	}
	const left = C - outline.halfWidth - 4;
	const right = C + outline.halfWidth + 4;
	return [
		[C, top, C, bottom],
		[left, C, right, C]
	];
}

/** Font size that fits ``text`` into ``width`` at roughly 0.62 em per character. */
export function fitFont(text: string, width: number, max = 40, min = 10): number {
	const chars = Math.max(1, text.length);
	return Math.max(min, Math.min(max, width / (chars * 0.62)));
}

/** Whether to draw a two-piece hard capsule (cap and body halves). */
export function isTwoPiece(
	shape: string | null | undefined,
	form: string | null | undefined,
	colors: readonly string[]
): boolean {
	if (shape !== 'capsule') return false;
	if (form) {
		const f = form.toUpperCase();
		return f.includes('CAPSULE') && !f.includes('TABLET');
	}
	return colors.length === 2;
}

/** Scale (0.55–1) so pills are drawn roughly in proportion to their size. */
export function sizeScale(sizeMm: number | null | undefined): number {
	if (!sizeMm) return 0.9;
	return Math.max(0.55, Math.min(1, sizeMm / 21));
}
