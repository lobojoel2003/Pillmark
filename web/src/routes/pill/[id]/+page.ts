import { error } from '@sveltejs/kit';
import { ApiError, getJson, type PillDetail, type PillSummary } from '#lib/api.ts';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	if (!/^\d{1,18}$/.test(params.id)) error(404, 'Pill not found');
	try {
		const [pill, similar] = await Promise.all([
			getJson<PillDetail>(fetch, `/v1/pills/${params.id}`),
			getJson<{ results: PillSummary[] }>(fetch, `/v1/pills/${params.id}/similar`).catch(() => ({
				results: []
			}))
		]);
		return { pill, similar: similar.results };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) error(404, 'Pill not found');
		error(503, e instanceof ApiError ? e.message : 'The pill database is not reachable.');
	}
};
