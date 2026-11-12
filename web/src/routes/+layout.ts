import { getJson, type Meta } from '#lib/api.ts';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch }) => {
	// Dataset size for the footer. The site still works if the API is down.
	try {
		return { meta: await getJson<Meta>(fetch, '/v1/meta') };
	} catch {
		return { meta: null };
	}
};
