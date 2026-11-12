// Liveness check for the web container. Reports the version without calling the API.
import { version } from '$app/env';

export const GET = () =>
	Response.json({ status: 'ok', version }, { headers: { 'cache-control': 'no-store' } });
