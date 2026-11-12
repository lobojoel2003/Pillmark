import { page } from 'vitest/browser';
import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';
import ColorPicker from './ColorPicker.svelte';
import ShapePicker from './ShapePicker.svelte';

describe('ShapePicker', () => {
	it('selects, deselects and reveals more shapes', async () => {
		const onchange = vi.fn();
		const { rerender } = render(ShapePicker, { value: null, colors: [], onchange });
		await page.getByRole('button', { name: 'Oval' }).click();
		expect(onchange).toHaveBeenLastCalledWith('oval');

		await rerender({ value: 'oval', colors: [], onchange });
		await expect
			.element(page.getByRole('button', { name: 'Oval' }))
			.toHaveAttribute('aria-pressed', 'true');
		await page.getByRole('button', { name: 'Oval' }).click();
		expect(onchange).toHaveBeenLastCalledWith(null);

		await expect.element(page.getByRole('button', { name: 'Gear' })).not.toBeInTheDocument();
		await page.getByRole('button', { name: /More shapes/ }).click();
		await expect.element(page.getByRole('button', { name: 'Gear' })).toBeInTheDocument();
	});
});

describe('ColorPicker', () => {
	it('keeps at most two colors, dropping the oldest', async () => {
		const onchange = vi.fn();
		render(ColorPicker, { value: ['white', 'blue'], onchange });
		await page.getByRole('button', { name: 'Yellow' }).click();
		expect(onchange).toHaveBeenLastCalledWith(['blue', 'yellow']);
		await page.getByRole('button', { name: /White/ }).click();
		expect(onchange).toHaveBeenLastCalledWith(['blue']);
	});
});
