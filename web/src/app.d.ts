// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	/** Web app version from package.json. */
	const __APP_VERSION__: string;
	/** CI build number, or "local". */
	const __APP_BUILD__: string;
	/** Short git commit of the build. */
	const __APP_COMMIT__: string;

	namespace App {
		interface Error {
			message: string;
		}
	}
}

export {};
