import { describe, expect, it } from 'vitest';
import {
	fitFont,
	isTwoPiece,
	outlineFor,
	regularPolygon,
	roundedPolygon,
	scoreLines,
	sizeScale
} from './geometry.ts';
import { SHAPES } from './vocab.ts';

describe('outlines', () => {
	it.each(SHAPES.map((s) => s.key))('draws %s as a closed path inside the box', (key) => {
		const outline = outlineFor(key);
		expect(outline.d).toMatch(/^M/);
		expect(outline.d.trim()).toMatch(/Z$/);
		const numbers = (outline.d.match(/-?\d+(\.\d+)?/g) ?? []).map(Number);
		expect(Math.min(...numbers)).toBeGreaterThanOrEqual(0);
		expect(Math.max(...numbers)).toBeLessThanOrEqual(200);
		expect(outline.textWidth).toBeGreaterThan(60);
		expect(outline.halfWidth).toBeGreaterThan(0);
	});

	it('falls back to round for unknown shapes', () => {
		expect(outlineFor('blob')).toEqual(outlineFor('round'));
		expect(outlineFor(null)).toEqual(outlineFor('round'));
	});

	it('centres regular polygons and keeps a flat bottom edge', () => {
		const hexagon = regularPolygon(6, 80);
		const ys = hexagon.map((p) => p[1]);
		const xs = hexagon.map((p) => p[0]);
		expect((Math.min(...ys) + Math.max(...ys)) / 2).toBeCloseTo(100);
		expect((Math.min(...xs) + Math.max(...xs)) / 2).toBeCloseTo(100);
		expect(ys.filter((y) => Math.abs(y - Math.max(...ys)) < 1e-6)).toHaveLength(2);
	});

	it('rounds every corner of a polygon', () => {
		const d = roundedPolygon(
			[
				[0, 0],
				[10, 0],
				[10, 10]
			],
			2
		);
		expect(d.match(/Q/g)).toHaveLength(3);
	});
});

describe('details', () => {
	it('places score lines for each kind of score', () => {
		const outline = outlineFor('round');
		expect(scoreLines(outline, null)).toEqual([]);
		expect(scoreLines(outline, 1)).toEqual([]);
		expect(scoreLines(outline, 2)).toHaveLength(1);
		expect(scoreLines(outline, 3)).toHaveLength(2);
		const cross = scoreLines(outline, 4);
		expect(cross).toHaveLength(2);
		expect(cross[1][1]).toBe(cross[1][3]); // horizontal
	});

	it('fits imprint text', () => {
		expect(fitFont('M', 120)).toBe(40);
		expect(fitFont('A VERY LONG IMPRINT TEXT', 120)).toBeGreaterThanOrEqual(10);
		expect(fitFont('A VERY LONG IMPRINT TEXT', 120)).toBeLessThan(10.5);
	});

	it('draws two-piece capsules only for capsule products', () => {
		expect(isTwoPiece('capsule', 'CAPSULE', ['blue'])).toBe(true);
		expect(isTwoPiece('capsule', 'TABLET, FILM COATED', ['white', 'blue'])).toBe(false);
		expect(isTwoPiece('capsule', null, ['white', 'blue'])).toBe(true);
		expect(isTwoPiece('round', 'CAPSULE', ['white'])).toBe(false);
	});

	it('scales drawings with pill size', () => {
		expect(sizeScale(null)).toBe(0.9);
		expect(sizeScale(5)).toBe(0.55);
		expect(sizeScale(21)).toBe(1);
		expect(sizeScale(30)).toBe(1);
	});
});
