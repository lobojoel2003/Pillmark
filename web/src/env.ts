import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	API_URL: {
		description: 'Where the web server reaches the Pillmark API, e.g. http://api:8000.',
		schema: (value) => (value || 'http://127.0.0.1:8000').replace(/\/+$/, '')
	},
	PUBLIC_API_URL: {
		public: true,
		description: 'Public address of the API, shown on the developers page.',
		schema: (value) => (value || '').replace(/\/+$/, '')
	}
});
