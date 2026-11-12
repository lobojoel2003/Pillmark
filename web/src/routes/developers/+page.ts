import { PUBLIC_API_URL } from '$app/env/public';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ url }) => ({
	// The public API address if one is configured, else this site's /api proxy.
	apiBase: PUBLIC_API_URL || `${url.origin}/api`,
	docsUrl: PUBLIC_API_URL ? `${PUBLIC_API_URL}/docs` : null
});
