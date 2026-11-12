from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from pillmark import importer
from pillmark.settings import Settings
from pillmark.sources import DailyMed, SourceDocument
from pillmark.spl import parse_spl
from pillmark.store import WriteResult, fingerprint, write_label

from .spl_factory import Product, make_daily_zip, make_spl

pytestmark = pytest.mark.db

SET_A = "11111111-1111-1111-1111-111111111111"
SET_B = "22222222-2222-2222-2222-222222222222"

Conn = psycopg.Connection[Any]


def _count(conn: Conn, table: str) -> int:
    row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def test_write_label_inserts_then_skips_same_version(conn: Conn) -> None:
    label = parse_spl(make_spl([Product(), Product(ndc="0000-0002")], set_id=SET_A))
    assert write_label(conn, label, source="test") == (WriteResult.UPSERTED, 2)
    assert write_label(conn, label, source="test") == (WriteResult.SKIPPED, 0)
    assert write_label(conn, label, source="test", force=True) == (WriteResult.UPSERTED, 2)
    assert _count(conn, "pills") == 2


def test_newer_version_replaces_pills_and_older_is_ignored(conn: Conn) -> None:
    v2 = parse_spl(make_spl([Product(imprint="NEW;2")], set_id=SET_A, version=2))
    v1 = parse_spl(make_spl([Product(imprint="OLD;1")], set_id=SET_A, version=1))
    write_label(conn, v2, source="test")
    assert write_label(conn, v1, source="test")[0] is WriteResult.SKIPPED
    row = conn.execute("SELECT imprint_key FROM pills").fetchone()
    assert row == ("NEW2",)


def test_label_without_pills_is_not_stored_and_removes_old_version(conn: Conn) -> None:
    syrup = Product(form="SOLUTION", imprint=None, shape=None, colors=[])
    assert write_label(conn, parse_spl(make_spl([syrup], set_id=SET_B)), source="t")[0] is (
        WriteResult.EMPTY
    )
    write_label(conn, parse_spl(make_spl([Product()], set_id=SET_A)), source="t")
    result = write_label(conn, parse_spl(make_spl([syrup], set_id=SET_A, version=2)), source="t")
    assert result[0] is WriteResult.DELETED
    assert _count(conn, "labels") == 0


def test_fingerprint_matches_repackagers_of_the_same_pill() -> None:
    a = parse_spl(make_spl([Product()], labeler="Maker")).pills[0]
    b = parse_spl(make_spl([Product(ndc="9999-0001")], labeler="Repackager")).pills[0]
    c = parse_spl(make_spl([Product(colors=["pink"])])).pills[0]
    assert fingerprint(a) == fingerprint(b) != fingerprint(c)


def test_groups_track_repackagers(conn: Conn) -> None:
    for set_id, labeler in [(SET_A, "Maker"), (SET_B, "Repackager")]:
        write_label(
            conn, parse_spl(make_spl([Product()], set_id=set_id, labeler=labeler)), source="t"
        )
    rows = conn.execute("SELECT group_size, is_primary FROM pills ORDER BY id").fetchall()
    assert rows == [(2, True), (2, False)]

    importer.load_documents(conn, [], source="cleanup", removed={SET_A})
    assert conn.execute("SELECT group_size, is_primary FROM pills").fetchall() == [(1, True)]


def test_load_documents_records_the_run(conn: Conn) -> None:
    docs = [
        SourceDocument("a", make_spl([Product()], set_id=SET_A)),
        SourceDocument("bad", b"<broken"),
        SourceDocument("vet", make_spl([Product()], set_id=SET_B, kind_code="50578-4")),
    ]
    stats = importer.load_documents(conn, docs, source="unit")
    assert (stats.documents, stats.labels_upserted, stats.errors) == (3, 1, 1)
    run = conn.execute("SELECT source, status, labels_upserted, errors FROM import_runs").fetchone()
    assert run == ("unit", "succeeded", 1, 1)


def test_load_documents_applies_removals(conn: Conn) -> None:
    importer.load_documents(
        conn, [SourceDocument("a", make_spl([Product()], set_id=SET_A))], source="first"
    )
    stats = importer.load_documents(conn, [], source="second", removed={SET_A})
    assert stats.labels_deleted == 1
    assert _count(conn, "labels") == 0


def test_import_path_reads_xml_and_zip(clean_db: str, tmp_path: Path) -> None:
    xml = tmp_path / "one.xml"
    xml.write_bytes(make_spl([Product()], set_id=SET_A))
    archive = tmp_path / "daily.zip"
    archive.write_bytes(make_daily_zip({SET_B: make_spl([Product()], set_id=SET_B)}))
    assert importer.import_path(clean_db, xml).labels_upserted == 1
    assert importer.import_path(clean_db, archive).labels_upserted == 1


# ---------------------------------------------------------------------------- nightly


def _record(conn: Conn, source: str, status: str = "succeeded") -> None:
    conn.execute("INSERT INTO import_runs (source, status) VALUES (%s, %s)", (source, status))
    conn.commit()


def test_pending_daily_dates_starts_with_yesterday(conn: Conn) -> None:
    assert importer.pending_daily_dates(conn, date(2026, 11, 12)) == [date(2026, 11, 11)]


def test_pending_daily_dates_catches_up_from_last_success(conn: Conn) -> None:
    _record(conn, "daily:2026-11-08")
    _record(conn, "daily:2026-11-10", status="failed")
    assert importer.pending_daily_dates(conn, date(2026, 11, 12)) == [
        date(2026, 11, 9),
        date(2026, 11, 10),
        date(2026, 11, 11),
    ]


def test_pending_daily_dates_is_capped(conn: Conn) -> None:
    _record(conn, "daily:2026-01-01")
    days = importer.pending_daily_dates(conn, date(2026, 11, 12), max_days=3)
    assert days == [date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11)]


def _mock_dailymed(handler: Callable[[httpx.Request], httpx.Response]) -> DailyMed:
    settings = Settings(dailymed_data_base="https://data.test")
    return DailyMed(settings, httpx.Client(transport=httpx.MockTransport(handler)))


def test_daily_catch_up_imports_each_missing_day(clean_db: str) -> None:
    archive = make_daily_zip({SET_A: make_spl([Product()], set_id=SET_A)})
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("11112026.zip"):
            return httpx.Response(200, content=archive)
        return httpx.Response(404)

    dm = _mock_dailymed(handler)
    with psycopg.connect(clean_db) as conn:
        _record(conn, "daily:2026-11-08")
    runs = importer.import_daily_catch_up(clean_db, today=date(2026, 11, 12), client=dm)
    assert [r.status for r in runs] == ["missing", "missing", "succeeded"]
    assert seen[-1].endswith("dm_spl_daily_update_11112026.zip")

    with psycopg.connect(clean_db) as conn:
        sources = [r[0] for r in conn.execute("SELECT source FROM import_runs ORDER BY id")]
        # 11-09 is old enough to give up on; 11-10 may still appear and is retried.
        assert sources == ["daily:2026-11-08", "daily:2026-11-09", "daily:2026-11-11"]
        assert importer.pending_daily_dates(conn, date(2026, 11, 12)) == [date(2026, 11, 10)]
