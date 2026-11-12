import { page } from 'vitest/browser';
import { describe, expect, it } from 'vitest';
import { render } from 'vitest-browser-svelte';
import PillGlyph from './PillGlyph.svelte';

describe('PillGlyph', () => {
	it('draws a described, accessible pill', async () => {
		render(PillGlyph, { shape: 'round', colors: ['pink'], imprint: 'LUPIN 10', score: 2 });
		const svg = page.getByRole('img', { name: 'Pink round pill with imprint LUPIN 10' });
		await expect.element(svg).toBeInTheDocument();
		// The imprint is drawn twice (highlight + engraving) on the face.
		expect(svg.element().querySelectorAll('text')).toHaveLength(2);
		// One score groove, drawn as a highlight and a line.
		expect(svg.element().querySelectorAll('line')).toHaveLength(2);
	});

	it('prints each side on its own half of a two-piece capsule', async () => {
		render(PillGlyph, {
			shape: 'capsule',
			colors: ['blue', 'yellow'],
			sides: ['TEVA', '3109'],
			form: 'CAPSULE'
		});
		const svg = page.getByRole('img');
		await expect.element(svg).toBeInTheDocument();
		const texts = [...svg.element().querySelectorAll('text')].map((t) => t.textContent);
		expect(texts).toEqual(['TEVA', '3109']);
	});

	it('shows a dashed placeholder before anything is chosen', async () => {
		render(PillGlyph, { muted: true, label: 'Nothing chosen yet' });
		const svg = page.getByRole('img', { name: 'Nothing chosen yet' });
		await expect.element(svg).toBeInTheDocument();
		expect(svg.element().querySelector('path[stroke-dasharray]')).not.toBeNull();
	});
});
