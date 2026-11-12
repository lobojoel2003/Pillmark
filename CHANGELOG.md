# Changelog

All notable changes to Pillmark are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). One version number covers the
API package, the web app, the Docker images and the git tag; see
[Releasing](README.md#releasing).

## [Unreleased]

## [1.0.0] - 2026-11-12

First public release.

### Added

- **Importer** for FDA Structured Product Labeling (SPL) files from DailyMed: reads
  imprint, color, shape, size, score and pill photos for every solid oral product,
  including each pill in a kit, and matches each product to its package label photo
  by NDC.
- **Nightly updates**: `pillmark import daily` catches up on every DailyMed daily
  update since the last successful run, and removes labels that DailyMed withdrew.
  `pillmark nightly` runs it on a schedule inside a container, and a GitHub Actions
  workflow runs it every night.
- **Bootstrap and development imports**: full DailyMed releases (`import full`), recent
  labels by drug name (`import drug`), labels by set id (`import setid`) and local
  files (`import file`).
- **PostgreSQL schema** with `pg_trgm` and `fuzzystrmatch`. Imprints are stored as
  tokens, a compact key and a look-alike folded key, so `IP 204`, `ip204`, `204 IP`
  and `1P 2O4` all find the same pill, and one wrong character still finds a close match.
- **Repackager grouping**: the same physical pill sold under many labels collapses into
  one result, with the other labelers listed on the pill's page.
- **Public FastAPI service** (`/v1/pills`, `/v1/pills/{id}`, `/v1/pills/{id}/similar`,
  `/v1/labels/{set_id}`, `/v1/vocab`, `/v1/meta`, `/v1/health`) with OpenAPI docs,
  CORS, gzip and cache headers. No key needed.
- **SvelteKit web app** with a visual picker that draws the pill as you tap a shape and
  colors, including two-tone capsules, score lines and the imprint. Results show the
  label photo next to the drawing. Search state lives in the URL so results can be
  shared. Works on phones, supports dark mode and keyboard use, and always shows
  Poison Control's number.
- **Docker images** for the API/importer and the web app, and a `docker-compose.yml`
  that runs the database, API, web app and nightly importer.
- **CI/CD**: lint, type checks and tests for both apps, end-to-end browser tests
  against a real database, Docker builds with a smoke test, CodeQL, Dependabot, a
  nightly import canary, and tag-driven releases that publish multi-arch images to
  GHCR plus Python and web build artifacts with checksums.

[Unreleased]: https://github.com/lobojoel2003/Pillmark/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/lobojoel2003/Pillmark/releases/tag/v1.0.0
