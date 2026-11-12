import { defineConfig, devices } from '@playwright/test';

// End-to-end tests run the built site against a real Pillmark API.
// Start the API first (see .github/workflows/ci.yml), then: npm run test:e2e
const port = 4173;
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.e2e.{ts,js}',
	fullyParallel: true,
	forbidOnly: Boolean(process.env.CI),
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
	use: {
		baseURL: `http://localhost:${port}`,
		trace: 'off',
		launchOptions: { executablePath }
	},
	projects: [
		{ name: 'desktop', use: { ...devices['Desktop Chrome'] } },
		{ name: 'mobile', use: { ...devices['Pixel 7'] } }
	],
	webServer: {
		command: `npm run build && npm run preview -- --port ${port} --strictPort`,
		port,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000,
		env: { API_URL: process.env.API_URL ?? 'http://127.0.0.1:8000' }
	}
});
