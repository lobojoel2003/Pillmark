import { expect, test } from '@playwright/test';

test.describe('identify a pill', () => {
	test('home explains what to do and how to get help', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: /Found a pill\?/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /1-800-222-1222/ }).first()).toHaveAttribute(
			'href',
			'tel:18002221222'
		);
		await expect(page.getByRole('img', { name: /Tap a shape and a color/ })).toBeVisible();
	});

	test('typing an imprint and tapping shape and color finds the pill', async ({ page }) => {
		await page.goto('/');
		await page.getByLabel("What's printed on it?").fill('lupin 10');
		await page.getByRole('button', { name: 'Round', exact: true }).click();
		await page.getByRole('button', { name: 'Pink', exact: true }).click();

		await expect(page).toHaveURL(/imprint=lupin\+10&shape=round&color=pink/);
		await expect(
			page.getByRole('img', { name: 'Pink round pill with imprint lupin 10', exact: true })
		).toBeVisible();

		const first = page.getByRole('link', { name: /^Lisinopril 10 mg, imprint LUPIN 10/ });
		await expect(first).toContainText('Exact imprint');
		await expect(
			first.getByRole('img', { name: /Pink round pill with imprint LUPIN 10/ })
		).toBeVisible();
	});

	test('imprints match in any order and with look-alike characters', async ({ page }) => {
		await page.goto('/?imprint=1P%20190');
		await expect(page.locator('a.result').first()).toContainText('Ibuprofen');
		await page.goto('/?imprint=367%20M');
		await expect(page.locator('a.result').first()).toContainText('Hydrocodone');
	});

	test('repackagers are grouped into one result', async ({ page }) => {
		await page.goto('/?imprint=M367');
		const first = page.locator('a.result').first();
		await expect(first).toContainText('+1 more');
		await expect(first).toContainText('Controlled CII');
	});

	test('two colors find a two-tone capsule', async ({ page }) => {
		await page.goto('/?shape=capsule&color=blue&color=yellow');
		await expect(page.getByRole('heading', { name: '1 match' })).toBeVisible();
		await expect(page.locator('a.result')).toContainText('Amoxicillin');
	});

	test('pills without an imprint can be found', async ({ page }) => {
		await page.goto('/');
		await page.getByLabel('It has no imprint').check();
		await page.getByRole('button', { name: 'Yellow', exact: true }).click();
		await expect(page.locator('a.result').first()).toContainText('Aspirin');
	});

	test('no matches gives advice', async ({ page }) => {
		await page.goto('/?imprint=ZZZZ999');
		await expect(page.getByRole('heading', { name: 'No matches' })).toBeVisible();
		await expect(page.getByText(/look-alike characters/)).toBeVisible();
	});

	test('start over clears everything', async ({ page }) => {
		await page.goto('/?imprint=M367&shape=capsule');
		await page.getByRole('button', { name: 'Start over' }).click();
		await expect(page).toHaveURL(/\/$/);
		await expect(page.getByLabel("What's printed on it?")).toHaveValue('');
	});
});

test.describe('pill page', () => {
	test('shows the drawing, label, ingredients and other labelers', async ({ page }) => {
		await page.goto('/?imprint=M367');
		await page.locator('a.result').first().click();

		await expect(page.getByRole('heading', { level: 1 })).toHaveText(
			'Hydrocodone Bitartrate and Acetaminophen'
		);
		await expect(page.getByText('10 mg / 325 mg', { exact: false }).first()).toBeVisible();
		await expect(page.getByRole('cell', { name: 'ACETAMINOPHEN' })).toBeVisible();
		await expect(
			page.getByRole('heading', { name: /Same pill from 1 other labeler/ })
		).toBeVisible();
		await expect(page.getByRole('link', { name: /Full label on DailyMed/ })).toHaveAttribute(
			'href',
			/dailymed\.nlm\.nih\.gov\/dailymed\/drugInfo\.cfm\?setid=/
		);

		await page.getByRole('link', { name: /Back to search/ }).click();
		await expect(page).toHaveURL(/imprint=M\+367/);
	});

	test('unknown pills are a friendly 404', async ({ page }) => {
		const response = await page.goto('/pill/99999999');
		expect(response?.status()).toBe(404);
		await expect(page.getByRole('heading', { name: 'Nothing here' })).toBeVisible();
	});
});

test.describe('site', () => {
	test('about and API pages', async ({ page }) => {
		await page.goto('/about');
		await expect(page.getByRole('heading', { name: 'A free, open pill identifier' })).toBeVisible();
		await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'API' }).click();
		await expect(page.getByRole('heading', { name: 'A free, public pill API' })).toBeVisible();
		await expect(page.locator('pre').first()).toContainText('/v1/pills?imprint=M%20367');
	});

	test('the API is proxied same-origin and the site reports health', async ({ request }) => {
		const search = await request.get('/api/v1/pills?imprint=TEVA3109');
		expect(search.ok()).toBe(true);
		expect((await search.json()).results[0].name).toBe('Amoxicillin');
		expect((await request.get('/api/v1/../../etc/passwd')).status()).toBe(404);

		const health = await request.get('/healthz');
		expect((await health.json()).status).toBe('ok');
	});
});
