from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pillmark import __version__
from pillmark.cli import build_parser, main, seconds_until

from .spl_factory import Product, make_daily_zip, make_spl

SET_A = "11111111-1111-1111-1111-111111111111"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"pillmark {__version__}"


def test_seconds_until_next_run() -> None:
    now = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)
    assert seconds_until("07:30", now) == 90 * 60
    assert seconds_until("05:00", now) == 23 * 3600
    assert seconds_until("06:00", now) == 24 * 3600


def test_rejects_bad_dates() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["import", "daily", "--date", "11/12/2026"])


@pytest.mark.db
def test_migrate_and_import_file(
    clean_db: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--database-url", clean_db, "migrate"]) == 0
    assert "up to date" in capsys.readouterr().out

    archive = tmp_path / "dm_spl_daily_update_11112026.zip"
    archive.write_bytes(make_daily_zip({SET_A: make_spl([Product()], set_id=SET_A)}))
    assert main(["--database-url", clean_db, "--json", "import", "file", str(archive)]) == 0
    [run] = json.loads(capsys.readouterr().out)
    assert run["status"] == "succeeded"
    assert run["labels_upserted"] == 1
    assert run["pills_written"] == 1
