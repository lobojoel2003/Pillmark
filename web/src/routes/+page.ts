import { ApiError, criteriaFromParams, hasCriteria, searchPills } from '#lib/api.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url, fetch }) => {
	const criteria = criteriaFromParams(url.searchParams);
	if (!hasCriteria(criteria)) return { criteria, search: null, error: null };
	try {
		return { criteria, search: await searchPills(fetch, criteria), error: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : 'Something went wrong with the search.';
		return { criteria, search: null, error: message };
	}
};
