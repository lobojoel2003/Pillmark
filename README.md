<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-dark.svg">
  <img src="docs/images/logo-light.svg" alt="Pillmark" width="420">
</picture>

**Identify a pill from its imprint, color and shape, fast.**<br>
Free, open source, with a public API and data refreshed nightly from FDA drug labels.

[![CI](https://github.com/lobojoel2003/Pillmark/actions/workflows/ci.yml/badge.svg)](https://github.com/lobojoel2003/Pillmark/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/lobojoel2003/Pillmark?sort=semver&color=0e7a64)](https://github.com/lobojoel2003/Pillmark/releases)
[![Nightly import](https://github.com/lobojoel2003/Pillmark/actions/workflows/nightly-import.yml/badge.svg)](https://github.com/lobojoel2003/Pillmark/actions/workflows/nightly-import.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
<br>
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-4169E1?logo=postgresql&logoColor=white)
![SvelteKit](https://img.shields.io/badge/SvelteKit-3-FF3E00?logo=svelte&logoColor=white)
![Docker](https://img.shields.io/badge/images-ghcr.io-2496ED?logo=docker&logoColor=white)

<img src="docs/images/picker.gif" alt="Tapping Oblong, Green and White draws a green and white capsule; typing ALM 672 prints it on the capsule and narrows the results to sertraline 200 mg" width="900">

</div>

> [!IMPORTANT]
> **If someone may have swallowed a pill that isn't theirs, call Poison Control at
> [1-800-222-1222](tel:18002221222) (US) or your local emergency number now.** Pillmark is
> not medical advice. Always confirm a pill with a pharmacist.

## Contents

- [Why Pillmark](#why-pillmark)
- [Features](#features)
- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [Loading data](#loading-data)
- [Public API](#public-api)
- [How matching works](#how-matching-works)
- [Architecture](#architecture)
- [Development](#development)
- [Configuration](#configuration)
- [Versioning and releases](#versioning-and-releases)
- [CI/CD](#cicd)
- [Data, limits and license](#data-limits-and-license)

## Why Pillmark

A loose pill on the floor, a parent's mixed-up pill organizer, a child who may have
swallowed something: people need to identify a pill from its imprint, color and shape,
fast.

- The U.S. National Library of Medicine **retired Pillbox**, its free pill identifier, on
  January 29, 2021, including its site, data, images and APIs. NLM points people to
  MedlinePlus and DailyMed but says
  ["these resources do not provide pill identification"](https://www.nlm.nih.gov/pubs/techbull/ja20/ja20_pillbox_discontinue.html).
- NLM ["has no plans to replace Pillbox"](https://www.route-fifty.com/digital-government/2021/05/nlm-pillbox-put-out-to-pasture/316051/),
  and manufacturers had stopped sending it content.
- Pillbox's final data, 8,693 photos and 83,925 rows of shape, color, imprint and size, is
  still downloadable but frozen. NLM says it
  ["should not be used for pill identification"](https://beautifulpublicdata.com/the-pillbox-database).

The free identifiers left are closed and ad-supported, with no public API. Pillmark is the
open alternative: it reads the same source manufacturers keep up to date, the FDA drug
labels that DailyMed publishes every day, and gives everyone a fast picker and a free API.

## Features

- **Draw it, don't describe it.** Tap a shape and one or two colors and the pill is drawn
  as you go: score lines, two-tone capsules and the imprint included. Nobody needs to know
  the word "oblong".
- **Label photo next to the drawing.** Every result shows the package label (or the pill
  photo when the label has one) beside a drawing made from the label's own description.
- **Forgiving imprint search.** `IP 204`, `ip204`, `204 IP` and `1P 2O4` find the same
  pill; one wrong character still finds a close match, ranked lower.
- **One result per pill.** Repackagers selling the same tablet are grouped, with the other
  labelers listed on the pill's page.
- **Fresh data.** A nightly job imports DailyMed's daily update and removes withdrawn labels.
- **Free public API.** JSON, no key, OpenAPI docs, CORS and cache headers.
- **Made for stressful moments.** Works on phones, shareable URLs, dark mode, keyboard and
  screen reader friendly, and Poison Control's number on every page.

## Screenshots

| Search by imprint and shape | Dark mode |
| --- | --- |
| ![Search for imprint SG with an oblong shape: gabapentin and naproxen results, each with a drawing and the package label photo](docs/images/identify.png) | ![Dark mode search for a pink round pill with imprint LUPIN](docs/images/identify-dark.png) |
| **Start page** | **Pill page** |
| ![Start page with the empty pill drawing, the picker and three example searches](docs/images/home.png) | ![Pill page for sertraline 200 mg showing the drawing, the package label, imprint sides, ingredients and other labelers](docs/images/pill-page.png) |

<p align="center">
  <img src="docs/images/mobile-picker.png" alt="Picker on a phone drawing a green and white capsule with imprint ALM" width="300">
  &nbsp;&nbsp;
  <img src="docs/images/mobile-results.png" alt="Results on a phone with drawings and label photos" width="300">
</p>

## Quick start

With Docker:

```bash
git clone https://github.com/lobojoel2003/Pillmark.git
cd Pillmark
docker compose up -d --build
```

```bash
docker compose run --rm api pillmark import drug metformin lisinopril atorvastatin amlodipine sertraline --per-name 20
```

Then open <http://localhost:3000> for the site and <http://localhost:8000/docs> for the API.
The `importer` service imports DailyMed's daily update every night at 07:30 UTC.

Or use the released images without cloning:

```bash
docker pull ghcr.io/lobojoel2003/pillmark-api:latest
docker pull ghcr.io/lobojoel2003/pillmark-web:latest
```

## Loading data

All imports are idempotent: a label is only rewritten when DailyMed has a newer version,
and every run is recorded in the `import_runs` table.

| Command | What it does |
| --- | --- |
| `pillmark import full` | Bootstrap: every human prescription and OTC label from DailyMed's full release (18 zips, several GB; streamed, use `--cache-dir` to keep them). |
| `pillmark import daily` | The nightly job: imports every daily update since the last successful one (up to a week back) and removes labels DailyMed withdrew. `--date YYYY-MM-DD` imports one day. |
| `pillmark nightly --at 07:30` | Runs `import daily` every day at that UTC time; used by the compose `importer` service. |
| `pillmark import drug NAME...` | Recent labels for a few drug names from the DailyMed web service. Good for development. |
| `pillmark import setid ID...` | Specific labels by DailyMed set id. |
| `pillmark import file PATH...` | Local SPL XML files or DailyMed zips (daily, weekly, monthly or full). |
| `pillmark migrate` | Creates or upgrades the schema (the API also does this at start with `PILLMARK_MIGRATE_ON_START=true`). |

A production setup typically runs `pillmark import full` once, then the nightly job.

## Public API

Base URL: wherever you run the API (`http://localhost:8000` locally). The web app also
proxies it same-origin at `/api`. Interactive docs are at `/docs`, the schema at
`/openapi.json`.

| Endpoint | Description |
| --- | --- |
| `GET /v1/pills` | Search. Parameters: `imprint`, `color` (repeat for two-tone), `shape`, `size` (mm, ± `size_tolerance`), `score`, `q` (name, ingredient or labeler), `has_imprint`, `include_discontinued`, `group`, `limit`, `offset`. |
| `GET /v1/pills/{id}` | One pill with ingredients, packages, marketing dates and its label. |
| `GET /v1/pills/{id}/similar` | The same pill sold by other labelers. |
| `GET /v1/labels/{set_id}` | A DailyMed label and all its pills. |
| `GET /v1/vocab` | Color and shape keys, with drawing colors. |
| `GET /v1/meta` | Version, build, commit and dataset size. |
| `GET /v1/health` | Liveness and database check. |

```bash
curl 'http://localhost:8000/v1/pills?imprint=alm%20672&limit=1'
```

```json
{
  "query": { "imprint": "alm 672", "imprint_key": "ALM672", "colors": [], "shape": null, "size_mm": null, "score": null, "name": null },
  "total": 2,
  "limit": 1,
  "offset": 0,
  "results": [
    {
      "id": 312,
      "set_id": "8c8bcba9-eaeb-aa44-f9ea-b580de55a439",
      "product_code": "52427-672",
      "name": "sertraline HCl",
      "generic_name": "sertraline hydrochloride",
      "strength": "200 mg",
      "dosage_form": "CAPSULE",
      "imprint": "ALM 672",
      "imprint_sides": ["ALM", "672"],
      "colors": ["green", "white"],
      "shape": "capsule",
      "size_mm": 19.0,
      "score": 1,
      "labeler": "Almatica Pharma LLC",
      "marketed": true,
      "dea_schedule": null,
      "photo_url": null,
      "label_image_url": "https://dailymed.nlm.nih.gov/dailymed/image.cfm?setid=8c8bcba9-eaeb-aa44-f9ea-b580de55a439&name=label-200mg.jpg",
      "match_score": 1.0,
      "group_size": 2
    }
  ],
  "disclaimer": "Pillmark is for information only and is not medical advice. ..."
}
```

Colors: `white yellow orange red pink purple blue turquoise green brown gray black`.
Shapes: `round oval capsule` (oblong) `rectangle square triangle diamond pentagon hexagon
heptagon octagon semi-circle tear trapezoid bullet clover gear double-circle freeform`.

## How matching works

Every SPL label lists, for each solid oral product, its imprint (`;` between sides),
colors, shape, size and score as coded values. Pillmark stores each imprint three ways:

| Form | `M;A;10` becomes | Used for |
| --- | --- | --- |
| tokens | `{M, A, 10}` | any order, partial imprints (GIN array index) |
| key | `MA10` | spacing and punctuation don't matter (B-tree and `pg_trgm` indexes) |
| fold | `MA10`, with `O→0`, `I/L→1` | look-alike characters |

Results are ranked in tiers: exact key, same tokens in another order, all typed tokens
present, look-alike match, prefix, substring, one character off (`fuzzystrmatch`) and
finally trigram similarity. Colors, shape, size and score filter exactly. Pills that are
the same physical product (same imprint, colors, shape, size, score, ingredient and
strength) share a fingerprint; the importer keeps each group's size and primary row up to
date, so a search returns one row per pill without grouping at query time.

In a benchmark on 160,000 pill rows (about the size of all DailyMed solid oral products),
imprint searches took 60–160 ms and filter-only searches under 100 ms.

## Architecture

```mermaid
flowchart LR
  subgraph DailyMed["DailyMed (NLM)"]
    D1[Daily update zips]
    D2[Full release zips]
    D3[Web services]
  end
  subgraph Importer["Python importer"]
    P[SPL parser<br/>lxml, no entities]
    S[Store<br/>upsert, groups]
  end
  DB[(PostgreSQL<br/>pg_trgm, fuzzystrmatch)]
  API[FastAPI<br/>public /v1 API]
  WEB[SvelteKit 3<br/>visual picker]
  U((People and apps))

  D1 -- nightly --> P
  D2 -- bootstrap --> P
  D3 -- dev --> P
  P --> S --> DB
  DB --> API
  API -- /api proxy --> WEB
  WEB --> U
  API --> U
  WEB -. label photos .-> DailyMed
```

```text
api/                     Python package `pillmark`
  src/pillmark/
    spl.py               SPL XML parser (products, kit parts, label photo matching)
    sources.py           DailyMed bulk files and web services
    importer.py          import runs, nightly catch-up
    store.py             upserts and repackager groups
    search.py            ranked search SQL
    api/                 FastAPI app and response models
    migrations/          SQL schema
  tests/                 pytest (unit + database), SPL factory, e2e fixture
web/                     SvelteKit 3 + Svelte 5 app
  src/lib/components/    PillGlyph (the drawing), pickers, result card
  src/lib/geometry.ts    19 pill outlines, score lines, text fitting
  src/routes/            pages and the /api proxy
  e2e/                   Playwright tests (desktop and mobile)
scripts/version.py       one version everywhere, release notes
.github/workflows/       CI, release, nightly import, CodeQL
```

## Development

Requirements: Python 3.11+, Node 22.17+, PostgreSQL 15+ (or Docker).

```bash
make install
make db
export DATABASE_URL=postgresql://pillmark:pillmark@localhost:5432/pillmark
make demo-data
make api
make web
```

`make api` serves <http://localhost:8000/docs>; `make web` serves <http://localhost:5173>.

| Command | Runs |
| --- | --- |
| `make lint` | ruff, ruff format, mypy (strict), prettier, eslint, svelte-check |
| `make test` | pytest (database tests need `PILLMARK_TEST_DATABASE_URL`) and Vitest unit and browser component tests |
| `make e2e` | Playwright tests of the built site against a running API, on desktop and mobile |
| `make up` / `make down` | the full stack in Docker |

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Configuration

| Variable | Used by | Default | Meaning |
| --- | --- | --- | --- |
| `DATABASE_URL` | API, importer | `postgresql://pillmark:pillmark@localhost:5432/pillmark` | PostgreSQL connection |
| `PILLMARK_MIGRATE_ON_START` | API | `false` | Apply migrations when the API starts |
| `PILLMARK_CORS_ORIGINS` | API | `["*"]` | Browser origins allowed to call the API (JSON list) |
| `PILLMARK_DB_POOL_MAX` | API | `10` | Connection pool size |
| `PILLMARK_BUILD`, `PILLMARK_COMMIT` | API, web build | `local` | Build number and commit, set by CI |
| `API_URL` | web | `http://127.0.0.1:8000` | Where the web server reaches the API |
| `PUBLIC_API_URL` | web | (empty) | Public API address shown on the API page |
| `ORIGIN`, `PORT`, `HOST` | web | | Standard [adapter-node](https://svelte.dev/docs/kit/adapter-node) settings |
| `PILLMARK_IMPORT_AT` | compose | `07:30` | UTC time of the nightly import |

## Versioning and releases

Pillmark follows [Semantic Versioning](https://semver.org). One version number, kept in
[`VERSION`](VERSION), covers the Python package, the web app, the Docker images and the
git tag; [`scripts/version.py`](scripts/version.py) keeps them in step and CI fails if
they drift. Every build also has a **build number** (the GitHub Actions run number) and a
commit, baked into the images and shown by `/v1/meta` and in the site footer, for example
`v1.0.0 (build 42)`.

### Releasing

```bash
make bump-patch
```

That updates `VERSION`, `api/pyproject.toml`, `pillmark/__init__.py`,
`web/package.json` and `package-lock.json`, and opens a new section in
[CHANGELOG.md](CHANGELOG.md). Fill in the changelog, then commit and tag:

```bash
git commit -am "Release 1.0.1"
git tag v1.0.1
git push origin main v1.0.1
```

Pushing the tag runs the [release workflow](.github/workflows/release.yml), which:

1. checks the tag matches every version file and the changelog,
2. runs the full CI suite,
3. builds the Python sdist and wheel and a tarball of the web build,
4. builds multi-arch (`amd64`, `arm64`) images with SBOM and provenance and pushes them to
   GHCR as `X.Y.Z`, `X.Y`, `X`, `latest`, `build-N` and `sha-abc1234`,
5. publishes a GitHub release with the changelog section, image pull commands, the build
   number and `SHA256SUMS.txt`.

You can also run the workflow by hand from the Actions tab: it releases the version in
`VERSION` and creates the tag. Versions with a suffix such as `1.1.0-rc.1` become
pre-releases and don't move `latest`.

## CI/CD

| Workflow | When | What |
| --- | --- | --- |
| [CI](.github/workflows/ci.yml) | push to `main`, pull requests | version check; API lint, types and tests on Python 3.11–3.13 against PostgreSQL 17; web lint, types, unit and component tests and build; Playwright end-to-end tests against a real API and database; Docker image builds and a `docker compose` smoke test |
| [Release](.github/workflows/release.yml) | `v*.*.*` tags, manual | CI, then artifacts, GHCR images and the GitHub release |
| [Nightly import](.github/workflows/nightly-import.yml) | daily 07:23 UTC, manual | imports DailyMed's daily update into the database in the `DATABASE_URL` secret; without the secret, imports yesterday's update into a scratch database as a canary for format changes |
| [CodeQL](.github/workflows/codeql.yml) | push, pull requests, weekly | code scanning for Python, TypeScript and workflows (public repositories) |
| [Dependabot](.github/dependabot.yml) | weekly | updates for pip, npm, GitHub Actions and Docker base images |

To keep a hosted database fresh, add a `DATABASE_URL` repository secret. GitHub pauses
scheduled workflows after 60 days without repository activity, so for a long-lived
deployment prefer the compose `importer` service or your platform's scheduler running
`pillmark import daily`.

## Data, limits and license

- **Source.** FDA Structured Product Labeling from
  [DailyMed](https://dailymed.nlm.nih.gov/dailymed/), U.S. National Library of Medicine.
  Label images are loaded from DailyMed.
- **Limits.** Pillmark only knows what manufacturers put in their labels. Imprints can be
  missing or inconsistent, colors are the manufacturer's names, and most labels have a
  photo of the package rather than the pill. Treat a match as a strong hint and confirm it
  with a pharmacist.
- **License.** [Apache-2.0](LICENSE). Security issues: see [SECURITY.md](SECURITY.md).
