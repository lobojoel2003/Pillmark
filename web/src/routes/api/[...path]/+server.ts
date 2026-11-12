// Same-origin proxy to the Pillmark API: the browser calls /api/v1/..., the web
// server forwards to API_URL. Only GET and HEAD are allowed; the API is read-only.
import { error } from '@sveltejs/kit';
import { API_URL } from '$app/env/private';
import type { RequestHandler } from './$types';

const FORWARDED_HEADERS = ['content-type', 'cache-control', 'x-pillmark-version', 'etag'];
const TIMEOUT_MS = 15_000;

const proxy: RequestHandler = async ({ params, url, fetch, request }) => {
	if (!/^(v1(\/.*)?|openapi\.json)$/.test(params.path)) error(404, 'Not found');

	let upstream: Response;
	try {
		upstream = await fetch(`${API_URL}/${params.path}${url.search}`, {
			method: request.method,
			headers: { accept: 'application/json' },
			signal: AbortSignal.timeout(TIMEOUT_MS)
		});
	} catch {
		return Response.json(
			{ detail: 'The pill database is not reachable right now. Please try again shortly.' },
			{ status: 503 }
		);
	}

	const headers = new Headers();
	for (const name of FORWARDED_HEADERS) {
		const value = upstream.headers.get(name);
		if (value) headers.set(name, value);
	}
	return new Response(upstream.body, { status: upstream.status, headers });
};

export const GET = proxy;
export const HEAD = proxy;
