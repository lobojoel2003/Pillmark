// Small color helpers for shading the pill drawings.

function parse(hex: string): [number, number, number] {
	const h = hex.replace('#', '');
	const full =
		h.length === 3
			? h
					.split('')
					.map((c) => c + c)
					.join('')
			: h;
	const n = Number.parseInt(full, 16);
	return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function format([r, g, b]: [number, number, number]): string {
	const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
	return '#' + [r, g, b].map((v) => clamp(v).toString(16).padStart(2, '0')).join('');
}

/** Mix two colors; ``amount`` 0 gives ``a``, 1 gives ``b``. */
export function mix(a: string, b: string, amount: number): string {
	const [ar, ag, ab] = parse(a);
	const [br, bg, bb] = parse(b);
	return format([ar + (br - ar) * amount, ag + (bg - ag) * amount, ab + (bb - ab) * amount]);
}

export function darken(hex: string, amount: number): string {
	return mix(hex, '#000000', amount);
}

export function lighten(hex: string, amount: number): string {
	return mix(hex, '#ffffff', amount);
}

/** Relative luminance (WCAG), 0 for black to 1 for white. */
export function luminance(hex: string): number {
	const channel = (v: number) => {
		const s = v / 255;
		return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
	};
	const [r, g, b] = parse(hex).map(channel);
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function isDark(hex: string): boolean {
	return luminance(hex) < 0.18;
}
