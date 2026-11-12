# pillmark (Python package)

The backend of [Pillmark](https://github.com/lobojoel2003/Pillmark), an open pill identifier:

- `pillmark import ...` downloads DailyMed SPL drug label files and loads imprint, color,
  shape, size and score into PostgreSQL.
- `pillmark serve` runs the public FastAPI service with fuzzy imprint search.

See the [main README](https://github.com/lobojoel2003/Pillmark#readme) for setup and API docs.
