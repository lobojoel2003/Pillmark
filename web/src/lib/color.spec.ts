import { describe, expect, it } from 'vitest';
import { darken, isDark, lighten, luminance, mix } from './color.ts';
import { COLORS, describePill } from './vocab.ts';

describe('color helpers', () => {
	it('mixes, darkens and lightens', () => {
		expect(mix('#000000', '#ffffff', 0.5)).toBe('#808080');
		expect(darken('#ffffff', 1)).toBe('#000000');
		expect(lighten('#000', 1)).toBe('#ffffff');
	});

	it('measures luminance', () => {
		expect(luminance('#ffffff')).toBeCloseTo(1);
		expect(luminance('#000000')).toBeCloseTo(0);
		expect(isDark(COLORS.find((c) => c.key === 'black')!.hex)).toBe(true);
		expect(isDark(COLORS.find((c) => c.key === 'white')!.hex)).toBe(false);
	});
});

describe('describePill', () => {
	it('writes a natural description', () => {
		expect(describePill('capsule', ['blue', 'yellow'], 'TEVA 3109')).toBe(
			'Blue and yellow oblong pill with imprint TEVA 3109'
		);
		expect(describePill(null, [], null)).toBe('Pill');
		expect(describePill('round', ['white'])).toBe('White round pill');
	});
});
