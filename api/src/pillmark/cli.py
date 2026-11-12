"""Command line: ``pillmark migrate``, ``pillmark import ...``, ``pillmark serve``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pillmark import __version__
from pillmark.settings import get_settings


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pillmark",
        description="Pillmark: open pill identifier built on DailyMed drug labels.",
    )
    parser.add_argument("--version", action="version", version=f"pillmark {__version__}")
    parser.add_argument(
        "--database-url", help="PostgreSQL URL (default: $DATABASE_URL or a local database)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug output")
    parser.add_argument("--json", action="store_true", help="print run results as JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="create or upgrade the database schema")

    imp = sub.add_parser("import", help="import DailyMed labels")
    isub = imp.add_subparsers(dest="source", required=True)

    daily = isub.add_parser(
        "daily", help="import DailyMed daily updates (default: catch up to yesterday)"
    )
    daily.add_argument("--date", type=_date, action="append", help="a specific day (repeatable)")
    daily.add_argument("--cache-dir", type=Path, help="keep downloaded zips here")
    daily.add_argument("--force", action="store_true", help="rewrite labels already stored")

    full = isub.add_parser("full", help="import DailyMed full releases (bootstrap, several GB)")
    full.add_argument(
        "--release",
        choices=["human_rx", "human_otc"],
        action="append",
        help="which release (repeatable; default: both)",
    )
    full.add_argument("--part", type=int, action="append", help="only these part numbers")
    full.add_argument("--cache-dir", type=Path, help="keep downloaded zips here")
    full.add_argument("--force", action="store_true", help="rewrite labels already stored")

    names = isub.add_parser("drug", help="import recent labels for drug names (development)")
    names.add_argument("names", nargs="+", help="drug names, e.g. metformin lisinopril")
    names.add_argument("--per-name", type=int, default=25, help="labels per name (default 25)")
    names.add_argument("--force", action="store_true")

    setids = isub.add_parser("setid", help="import labels by DailyMed set id")
    setids.add_argument("set_ids", nargs="+")
    setids.add_argument("--force", action="store_true")

    files = isub.add_parser("file", help="import local SPL XML files or DailyMed zips")
    files.add_argument("paths", nargs="+", type=Path)
    files.add_argument(
        "--all-folders", action="store_true", help="also read animal/ and other/ folders"
    )
    files.add_argument("--force", action="store_true")

    nightly = sub.add_parser(
        "nightly", help="run the daily import every day at a fixed UTC time (for a container)"
    )
    nightly.add_argument("--at", default="07:30", help="UTC time of day, HH:MM (default 07:30)")
    nightly.add_argument("--now", action="store_true", help="also run once at startup")
    nightly.add_argument("--cache-dir", type=Path, help="keep downloaded zips here")

    serve = sub.add_parser("serve", help="run the API with uvicorn")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.add_argument("--workers", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    url = args.database_url or get_settings().database_url

    if args.command == "migrate":
        from pillmark.db import migrate

        applied = migrate(url)
        print(f"applied: {', '.join(applied)}" if applied else "schema is up to date")
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "pillmark.api.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            proxy_headers=True,
        )
        return 0

    from pillmark import importer
    from pillmark.db import migrate

    migrate(url)
    if args.command == "nightly":
        return run_nightly(url, args.at, run_now=args.now, cache_dir=args.cache_dir)

    if args.source == "daily":
        if args.date:
            runs = [
                importer.import_daily(url, d, cache_dir=args.cache_dir, force=args.force)
                for d in args.date
            ]
        else:
            runs = importer.import_daily_catch_up(url, cache_dir=args.cache_dir)
    elif args.source == "full":
        runs = importer.import_full_release(
            url,
            args.release or ["human_rx", "human_otc"],
            parts=args.part,
            cache_dir=args.cache_dir,
            force=args.force,
        )
    elif args.source == "drug":
        runs = [
            importer.import_drug_names(url, args.names, per_name=args.per_name, force=args.force)
        ]
    elif args.source == "setid":
        runs = [importer.import_set_ids(url, args.set_ids, force=args.force)]
    else:
        runs = [
            importer.import_path(url, p, all_folders=args.all_folders, force=args.force)
            for p in args.paths
        ]

    if args.json:
        print(json.dumps([asdict(r) for r in runs], indent=2, default=str))
    else:
        for run in runs:
            print(run.summary())
        if not runs:
            print("nothing to import")
    return 1 if any(r.status == "failed" for r in runs) else 0


def seconds_until(at: str, now: datetime) -> float:
    """Seconds from ``now`` (UTC) until the next ``HH:MM`` UTC."""
    hour, minute = (int(part) for part in at.split(":", 1))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_nightly(
    url: str, at: str, *, run_now: bool = False, cache_dir: Path | None = None
) -> int:  # pragma: no cover - runs forever
    from pillmark import importer

    log = logging.getLogger("pillmark.nightly")
    seconds_until(at, datetime.now(UTC))  # validate --at early
    first = run_now
    while True:
        if not first:
            wait = seconds_until(at, datetime.now(UTC))
            log.info("next import at %s UTC, in %.0f minutes", at, wait / 60)
            time.sleep(wait)
        first = False
        try:
            for run in importer.import_daily_catch_up(url, cache_dir=cache_dir):
                log.info(run.summary())
        except Exception:
            log.exception("nightly import failed; will retry at the next scheduled time")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
