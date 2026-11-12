import { describe, expect, it } from 'vitest';
import {
	criteriaFromParams,
	criteriaToApiParams,
	criteriaToParams,
	emptyCriteria,
	hasCriteria,
	matchLabel,
	pillTitle
} from './api.ts';

describe('criteria and URLs', () => {
	it('round-trips through page search params', () => {
		const criteria = {
			...emptyCriteria(),
			imprint: 'M 367',
			shape: 'capsule' as const,
			colors: ['blue' as const, 'yellow' as const],
			score: 2,
			size: 18,
			name: 'teva'
		};
		const params = criteriaToParams(criteria);
		expect(params.toString()).toBe(
			'imprint=M+367&shape=capsule&color=blue&color=yellow&score=2&size=18&q=teva'
		);
		expect(criteriaFromParams(params)).toEqual(criteria);
	});

	it('ignores unknown and out-of-range values', () => {
		const c = criteriaFromParams(
			new URLSearchParams('shape=blob&color=mauve,white&color=red&color=blue&score=9&size=abc')
		);
		expect(c.shape).toBeNull();
		expect(c.colors).toEqual(['white', 'red']);
		expect(c.score).toBeNull();
		expect(c.size).toBeNull();
	});

	it('maps "no imprint" to the API has_imprint filter', () => {
		const c = criteriaFromParams(new URLSearchParams('no_imprint=1&shape=round'));
		expect(c.noImprint).toBe(true);
		expect(criteriaToApiParams(c).get('has_imprint')).toBe('false');
		expect(criteriaToParams(c).toString()).toBe('no_imprint=1&shape=round');
	});

	it('builds API params with paging', () => {
		const c = { ...emptyCriteria(), imprint: ' ip 204 ' };
		expect(criteriaToApiParams(c, 24).toString()).toBe('imprint=ip+204&limit=24&offset=24');
	});

	it('knows when there is something to search for', () => {
		expect(hasCriteria(emptyCriteria())).toBe(false);
		expect(hasCriteria({ ...emptyCriteria(), imprint: '   ' })).toBe(false);
		expect(hasCriteria({ ...emptyCriteria(), colors: ['white'] })).toBe(true);
	});
});

describe('wording', () => {
	it('describes match quality only for imprint searches', () => {
		expect(matchLabel(1, true)).toBe('Exact imprint');
		expect(matchLabel(0.9, true)).toBe('Imprint matches');
		expect(matchLabel(0.75, true)).toBe('Partial imprint');
		expect(matchLabel(0.65, true)).toBe('Close imprint');
		expect(matchLabel(1, false)).toBeNull();
	});

	it('titles pills by name, then generic name', () => {
		expect(pillTitle({ name: 'Advil', generic_name: 'ibuprofen' })).toBe('Advil');
		expect(pillTitle({ name: null, generic_name: 'ibuprofen' })).toBe('ibuprofen');
		expect(pillTitle({ name: null, generic_name: null })).toBe('Unnamed product');
	});
});
