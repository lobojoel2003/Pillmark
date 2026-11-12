# Contributing to Pillmark

Thanks for helping. Pillmark is a small codebase with two parts:

| Folder | What it is |
| --- | --- |
| `api/` | Python 3.11+: the DailyMed importer, the PostgreSQL schema and the FastAPI service |
| `web/` | SvelteKit 3 + Svelte 5: the visual pill picker and pill pages |

## Set up

You need Python 3.11+, Node 22.17+ and PostgreSQL 15+ (or Docker).

```bash
make install        # API venv + web dependencies
make db             # PostgreSQL in Docker on :5432
export DATABASE_URL=postgresql://pillmark:pillmark@localhost:5432/pillmark
make demo-data      # a few hundred real labels from DailyMed
make api            # http://localhost:8000/docs
make web            # http://localhost:5173
```

## Before you open a pull request

```bash
make lint
PILLMARK_TEST_DATABASE_URL=postgresql://pillmark:pillmark@localhost:5432/pillmark_test make test
```

- API tests that need a database are skipped without `PILLMARK_TEST_DATABASE_URL`. The
  database they point at is wiped, so use a throwaway one.
- Browser tests (`make e2e`) build the site and run it against the API at `API_URL`.
  Load the fixture first: `cd api && python -m tests.e2e_fixture e2e.zip && .venv/bin/pillmark import file e2e.zip`.
- Add an entry under `## [Unreleased]` in `CHANGELOG.md` for anything a user would notice.
- The color and shape lists exist in both `api/src/pillmark/vocab.py` and
  `web/src/lib/vocab.ts`; a test fails if they drift apart.

## Data

Pillmark only shows what manufacturers put in their FDA labels. If a pill is wrong in
Pillmark because its label is wrong, the fix belongs in the label, not in code. Parser
bugs are very welcome though: include the DailyMed set id.
