# Pillmark web app

SvelteKit 3 front end for [Pillmark](../README.md): the visual pill picker, results and pill pages.

```bash
npm ci
API_URL=http://127.0.0.1:8000 npm run dev   # needs the API running
npm run lint && npm run check && npm test   # lint, types, unit + component tests
npx playwright test                         # browser tests against API_URL
```

The browser talks to `/api/*` on the same origin; the web server forwards those
requests to `API_URL`. See the [main README](../README.md) for everything else.
