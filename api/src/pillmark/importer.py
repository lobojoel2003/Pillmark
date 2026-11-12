"""Import DailyMed labels into the database.

Every import is recorded in ``import_runs``. The nightly job calls
:func:`import_daily_catch_up`, which reads each daily update since the last
successful one, so a missed night is picked up the next time it runs.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg

from pillmark.db import connect
from pillmark.sources import (
    HUMAN_FOLDERS,
    DailyMed,
    SourceDocument,
    SourceNotFound,
    iter_archive,
    removed_set_ids,
)
from pillmark.spl import SPLParseError, parse_spl
from pillmark.store import WriteResult, delete_labels, refresh_groups, write_label

log = logging.getLogger(__name__)

DEFAULT_KINDS: frozenset[str] = frozenset({"rx", "otc"})

#: DailyMed keeps roughly a week of daily files online.
MAX_CATCH_UP_DAYS = 7


@dataclass(slots=True)
class RunStats:
    source: str
    documents: int = 0
    labels_upserted: int = 0
    labels_skipped: int = 0
    labels_deleted: int = 0
    pills_written: int = 0
    errors: int = 0
    status: str = "running"
    message: str | None = None
    error_samples: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.source}: {self.status}; {self.documents} documents, "
            f"{self.labels_upserted} labels written, {self.labels_skipped} unchanged, "
            f"{self.labels_deleted} removed, {self.pills_written} pills, {self.errors} errors"
        )


def _start_run(conn: psycopg.Connection[Any], source: str) -> int:
    row = conn.execute(
        "INSERT INTO import_runs (source) VALUES (%s) RETURNING id", (source,)
    ).fetchone()
    conn.commit()
    assert row is not None
    return int(row[0])


def _finish_run(conn: psycopg.Connection[Any], run_id: int, stats: RunStats) -> None:
    conn.execute(
        """
        UPDATE import_runs SET status = %s, finished_at = now(), documents = %s,
            labels_upserted = %s, labels_skipped = %s, labels_deleted = %s,
            pills_written = %s, errors = %s, message = %s
        WHERE id = %s
        """,
        (
            stats.status,
            stats.documents,
            stats.labels_upserted,
            stats.labels_skipped,
            stats.labels_deleted,
            stats.pills_written,
            stats.errors,
            stats.message,
            run_id,
        ),
    )
    conn.commit()


def load_documents(
    conn: psycopg.Connection[Any],
    documents: Iterable[SourceDocument],
    *,
    source: str,
    kinds: frozenset[str] | None = DEFAULT_KINDS,
    removed: set[str] | None = None,
    force: bool = False,
    commit_every: int = 200,
) -> RunStats:
    """Parse and store documents, recording the run in ``import_runs``."""
    stats = RunStats(source=source)
    run_id = _start_run(conn, source)
    touched: set[str] = set()
    try:
        pending = 0
        for doc in documents:
            stats.documents += 1
            try:
                label = parse_spl(doc.xml)
            except SPLParseError as exc:
                stats.errors += 1
                if len(stats.error_samples) < 10:
                    stats.error_samples.append(f"{doc.name}: {exc}")
                log.warning("skipping %s: %s", doc.name, exc)
                continue
            if kinds is not None and label.kind not in kinds:
                continue
            result, pills = write_label(conn, label, source=source, force=force, touched=touched)
            if result is WriteResult.UPSERTED:
                stats.labels_upserted += 1
                stats.pills_written += pills
            elif result is WriteResult.SKIPPED:
                stats.labels_skipped += 1
            elif result is WriteResult.DELETED:
                stats.labels_deleted += 1
            pending += 1
            if pending >= commit_every:
                refresh_groups(conn, touched)
                touched.clear()
                conn.commit()
                pending = 0
                log.info(stats.summary())
        if removed:
            stats.labels_deleted += delete_labels(conn, removed, touched)
        refresh_groups(conn, touched)
        conn.commit()
        stats.status = "succeeded"
    except BaseException as exc:
        conn.rollback()
        stats.status = "failed"
        stats.message = f"{type(exc).__name__}: {exc}"[:2000]
        _finish_run(conn, run_id, stats)
        raise
    if stats.error_samples:
        stats.message = "; ".join(stats.error_samples)[:2000]
    _finish_run(conn, run_id, stats)
    log.info(stats.summary())
    return stats


# --------------------------------------------------------------------------- commands


def import_path(
    url: str,
    path: Path,
    *,
    all_folders: bool = False,
    kinds: frozenset[str] | None = DEFAULT_KINDS,
    force: bool = False,
) -> RunStats:
    """Import a local SPL XML file or DailyMed zip (daily, weekly, monthly or full)."""
    with connect(url) as conn:
        if path.suffix.lower() == ".xml":
            docs: Iterable[SourceDocument] = [SourceDocument(path.name, path.read_bytes())]
            return load_documents(conn, docs, source=f"file:{path.name}", kinds=kinds, force=force)
        folders = None if all_folders else HUMAN_FOLDERS
        return load_documents(
            conn,
            iter_archive(path, folders),
            source=f"file:{path.name}",
            kinds=kinds,
            removed=removed_set_ids(path),
            force=force,
        )


def _daily_source(day: date) -> str:
    return f"daily:{day.isoformat()}"


def import_daily(
    url: str,
    day: date,
    *,
    client: DailyMed | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
    today: date | None = None,
) -> RunStats:
    """Import one DailyMed daily update file."""
    today = today or datetime.now(UTC).date()
    source = _daily_source(day)
    own_client = client is None
    dm = client or DailyMed()
    try:
        with connect(url) as conn:
            try:
                with dm.download(dm.daily_url(day), cache_dir) as path:
                    return load_documents(
                        conn,
                        iter_archive(path, HUMAN_FOLDERS),
                        source=source,
                        removed=removed_set_ids(path),
                        force=force,
                    )
            except SourceNotFound:
                stats = RunStats(source=source, status="missing")
                stats.message = f"no daily update published for {day.isoformat()}"
                # A file may still appear for the last couple of days; only give up on
                # older dates so the next nightly run retries recent ones.
                if (today - day).days > 2:
                    _finish_run(conn, _start_run(conn, source), stats)
                log.warning(stats.message)
                return stats
    finally:
        if own_client:
            dm.close()


def pending_daily_dates(
    conn: psycopg.Connection[Any], today: date, max_days: int = MAX_CATCH_UP_DAYS
) -> list[date]:
    """Daily update dates still to import, oldest first, ending yesterday.

    A fresh database starts with yesterday. After that, every day in the last
    ``max_days`` without a finished run is returned, so a failed or late night
    is retried until it succeeds or is too old to still be online.
    """
    rows = conn.execute(
        """
        SELECT DISTINCT substring(source FROM 7)::date FROM import_runs
        WHERE source LIKE 'daily:%%' AND status IN ('succeeded', 'missing')
        """
    ).fetchall()
    done: set[date] = {r[0] for r in rows}
    yesterday = today - timedelta(days=1)
    if not done:
        return [yesterday]
    day = max(min(done), today - timedelta(days=max_days))
    days: list[date] = []
    while day <= yesterday:
        if day not in done:
            days.append(day)
        day += timedelta(days=1)
    return days


def import_daily_catch_up(
    url: str,
    *,
    today: date | None = None,
    client: DailyMed | None = None,
    cache_dir: Path | None = None,
) -> list[RunStats]:
    """Import every daily update since the last successful one (the nightly job)."""
    today = today or datetime.now(UTC).date()
    with connect(url) as conn:
        days = pending_daily_dates(conn, today)
    if not days:
        log.info("daily updates are up to date")
        return []
    own_client = client is None
    dm = client or DailyMed()
    try:
        return [import_daily(url, day, client=dm, cache_dir=cache_dir, today=today) for day in days]
    finally:
        if own_client:
            dm.close()


def import_full_release(
    url: str,
    kinds: Iterable[str] = ("human_rx", "human_otc"),
    *,
    parts: Iterable[int] | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
) -> list[RunStats]:
    """Import DailyMed full release archives (several GB; used to bootstrap a database)."""
    wanted_parts = set(parts) if parts else None
    results: list[RunStats] = []
    with DailyMed() as dm, connect(url) as conn:
        for kind in kinds:
            for number, part_url in enumerate(dm.full_release_urls(kind), start=1):
                if wanted_parts and number not in wanted_parts:
                    continue
                with dm.download(part_url, cache_dir) as path:
                    results.append(
                        load_documents(
                            conn,
                            iter_archive(path, HUMAN_FOLDERS),
                            source=f"full:{kind}:part{number}",
                            force=force,
                        )
                    )
    return results


def import_set_ids(
    url: str,
    set_ids: Iterable[str],
    *,
    kinds: frozenset[str] | None = None,
    force: bool = False,
) -> RunStats:
    """Import specific labels through the DailyMed web service."""
    ids = list(dict.fromkeys(s.lower() for s in set_ids))

    def documents(dm: DailyMed) -> Iterable[SourceDocument]:
        for set_id in ids:
            try:
                yield dm.spl_document(set_id)
            except SourceNotFound:
                log.warning("DailyMed has no label with set id %s", set_id)

    with DailyMed() as dm, connect(url) as conn:
        return load_documents(
            conn, documents(dm), source=f"setid:{len(ids)}", kinds=kinds, force=force
        )


def import_drug_names(
    url: str, names: Iterable[str], *, per_name: int = 25, force: bool = False
) -> RunStats:
    """Import the most recent labels for each drug name (handy for development)."""
    names = list(names)
    with DailyMed() as dm:
        set_ids: list[str] = []
        for name in names:
            found = dm.set_ids_for_drug(name, per_name)
            log.info("%s: %d labels", name, len(found))
            set_ids.extend(found)
    return import_set_ids(url, set_ids, kinds=DEFAULT_KINDS, force=force)
