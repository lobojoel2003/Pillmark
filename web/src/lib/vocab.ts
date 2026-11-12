// Colors and shapes the API understands. Keep in sync with api/src/pillmark/vocab.py
// (api/tests/test_vocab_sync.py checks that they match).

export type ColorKey =
	| 'white'
	| 'yellow'
	| 'orange'
	| 'red'
	| 'pink'
	| 'purple'
	| 'blue'
	| 'turquoise'
	| 'green'
	| 'brown'
	| 'gray'
	| 'black';

export type ShapeKey =
	| 'round'
	| 'oval'
	| 'capsule'
	| 'rectangle'
	| 'square'
	| 'triangle'
	| 'diamond'
	| 'pentagon'
	| 'hexagon'
	| 'heptagon'
	| 'octagon'
	| 'semi-circle'
	| 'tear'
	| 'trapezoid'
	| 'bullet'
	| 'clover'
	| 'gear'
	| 'double-circle'
	| 'freeform';

export interface Color {
	key: ColorKey;
	label: string;
	hex: string;
}

export interface Shape {
	key: ShapeKey;
	label: string;
	hint: string;
}

export const COLORS: readonly Color[] = [
	{ key: 'white', label: 'White', hex: '#F6F4EE' },
	{ key: 'yellow', label: 'Yellow', hex: '#F2D04B' },
	{ key: 'orange', label: 'Orange', hex: '#EE8A3A' },
	{ key: 'red', label: 'Red', hex: '#D2453C' },
	{ key: 'pink', label: 'Pink', hex: '#F2A0B8' },
	{ key: 'purple', label: 'Purple', hex: '#8A63C8' },
	{ key: 'blue', label: 'Blue', hex: '#4F86D9' },
	{ key: 'turquoise', label: 'Turquoise', hex: '#3FB6B2' },
	{ key: 'green', label: 'Green', hex: '#5DAA68' },
	{ key: 'brown', label: 'Brown', hex: '#9A6A43' },
	{ key: 'gray', label: 'Gray', hex: '#B5B8BD' },
	{ key: 'black', label: 'Black', hex: '#2B2B2E' }
];

export const SHAPES: readonly Shape[] = [
	{ key: 'round', label: 'Round', hint: 'A circle seen from above' },
	{ key: 'oval', label: 'Oval', hint: 'An egg-like ellipse' },
	{ key: 'capsule', label: 'Oblong', hint: 'Long with round ends, like a capsule' },
	{ key: 'rectangle', label: 'Rectangle', hint: 'Four straight sides, longer than wide' },
	{ key: 'square', label: 'Square', hint: 'Four equal sides' },
	{ key: 'triangle', label: 'Triangle', hint: 'Three sides' },
	{ key: 'diamond', label: 'Diamond', hint: 'A square on its corner' },
	{ key: 'pentagon', label: 'Pentagon', hint: 'Five sides' },
	{ key: 'hexagon', label: 'Hexagon', hint: 'Six sides' },
	{ key: 'octagon', label: 'Octagon', hint: 'Eight sides' },
	{ key: 'semi-circle', label: 'Half circle', hint: 'A circle cut in half' },
	{ key: 'tear', label: 'Teardrop', hint: 'Round at one end, pointed at the other' },
	{ key: 'trapezoid', label: 'Trapezoid', hint: 'Four sides, two parallel' },
	{ key: 'bullet', label: 'Bullet', hint: 'Flat at one end, round at the other' },
	{ key: 'heptagon', label: 'Heptagon', hint: 'Seven sides' },
	{ key: 'clover', label: 'Clover', hint: 'Four rounded lobes' },
	{ key: 'gear', label: 'Gear', hint: 'Notched edges, like a cog' },
	{ key: 'double-circle', label: 'Double circle', hint: 'Two overlapping circles' },
	{ key: 'freeform', label: 'Other', hint: 'Any other shape' }
];

/** Shapes shown before "More shapes"; together they cover nearly every pill. */
export const COMMON_SHAPES: readonly ShapeKey[] = [
	'round',
	'oval',
	'capsule',
	'rectangle',
	'triangle',
	'diamond',
	'square',
	'pentagon',
	'hexagon',
	'octagon'
];

export const SCORES = [
	{ value: 1, label: 'No line', hint: 'Smooth, not meant to be split' },
	{ value: 2, label: 'One line', hint: 'Splits in half' },
	{ value: 3, label: 'Two lines', hint: 'Splits in thirds' },
	{ value: 4, label: 'Cross', hint: 'Splits in quarters' }
] as const;

const colorMap = new Map(COLORS.map((c) => [c.key, c]));
const shapeMap = new Map(SHAPES.map((s) => [s.key, s]));

export function isColorKey(value: string): value is ColorKey {
	return colorMap.has(value as ColorKey);
}

export function isShapeKey(value: string): value is ShapeKey {
	return shapeMap.has(value as ShapeKey);
}

export function colorOf(key: string): Color | undefined {
	return colorMap.get(key as ColorKey);
}

export function shapeOf(key: string): Shape | undefined {
	return shapeMap.get(key as ShapeKey);
}

/** "White and blue oblong pill" style description for screen readers and captions. */
export function describePill(
	shape: string | null | undefined,
	colors: readonly string[],
	imprint?: string | null
): string {
	const colorText = colors.length
		? colors.map((c) => colorOf(c)?.label.toLowerCase() ?? c).join(' and ')
		: '';
	const shapeText = shape ? (shapeOf(shape)?.label.toLowerCase() ?? shape) : '';
	const body = [colorText, shapeText, 'pill'].filter(Boolean).join(' ');
	const sentence = body.charAt(0).toUpperCase() + body.slice(1);
	return imprint ? `${sentence} with imprint ${imprint}` : sentence;
}
