from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pytest

from pillmark.settings import Settings
from pillmark.sources import (
    DailyMed,
    SourceNotFound,
    image_url,
    iter_archive,
    removed_set_ids,
    set_id_from_name,
)

from .spl_factory import Product, make_daily_zip, make_spl

SET_A = "11111111-1111-1111-1111-111111111111"
SET_B = "22222222-2222-2222-2222-222222222222"
SET_GONE = "33333333-3333-3333-3333-333333333333"


def test_set_id_from_name() -> None:
    assert set_id_from_name(f"prescription/20261111_{SET_A.upper()}.zip") == SET_A
    assert set_id_from_name("files_added.txt") is None


def test_iter_archive_reads_nested_zips_and_filters_folders() -> None:
    data = make_daily_zip(
        {SET_A: make_spl([Product()], set_id=SET_A)},
        extra_folders={
            "otc": {SET_B: make_spl([Product()], set_id=SET_B)},
            "animal": {SET_GONE: make_spl([Product()], set_id=SET_GONE)},
        },
    )
    docs = list(iter_archive(io.BytesIO(data)))
    assert len(docs) == 2
    assert all(d.images == ("label.jpg",) for d in docs)
    assert {d.name.split("/")[0] for d in docs} == {"prescription", "otc"}
    assert len(list(iter_archive(io.BytesIO(data), folders=None))) == 3


def test_iter_archive_reads_a_single_label_zip(tmp_path: Path) -> None:
    path = tmp_path / "label.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("doc.xml", make_spl([Product()]))
        z.writestr("pill.jpg", b"")
    [doc] = list(iter_archive(path))
    assert doc.images == ("pill.jpg",)


def test_iter_archive_skips_corrupt_inner_zips() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("prescription/20261111_x.zip", b"not a zip")
    assert list(iter_archive(io.BytesIO(buf.getvalue()))) == []


def test_removed_set_ids_ignores_replaced_versions() -> None:
    data = make_daily_zip({SET_A: make_spl([Product()], set_id=SET_A)}, deleted=[SET_A, SET_GONE])
    assert removed_set_ids(io.BytesIO(data)) == {SET_GONE}


def test_image_url() -> None:
    url = image_url("https://dailymed.nlm.nih.gov/dailymed", SET_A, "my pill.jpg")
    assert url == (
        f"https://dailymed.nlm.nih.gov/dailymed/image.cfm?setid={SET_A}&name=my+pill.jpg"
    )
    assert image_url("https://x", SET_A, None) is None


# ----------------------------------------------------------------------------- client


def _client(handler: httpx.MockTransport) -> DailyMed:
    settings = Settings(
        dailymed_base="https://dm.test/dailymed", dailymed_data_base="https://data.test"
    )
    return DailyMed(settings, httpx.Client(transport=handler))


def test_urls() -> None:
    dm = _client(httpx.MockTransport(lambda r: httpx.Response(200)))
    assert dm.daily_url(date(2026, 1, 2)) == "https://data.test/dm_spl_daily_update_01022026.zip"
    assert (
        dm.full_release_urls("human_rx")[-1]
        == "https://data.test/dm_spl_release_human_rx_part6.zip"
    )
    with pytest.raises(ValueError, match="unknown release"):
        dm.full_release_urls("animal")


def test_download_streams_to_a_temporary_file(tmp_path: Path) -> None:
    dm = _client(httpx.MockTransport(lambda r: httpx.Response(200, content=b"zipdata")))
    with dm.download("https://data.test/a.zip") as path:
        assert path.read_bytes() == b"zipdata"
    assert not path.exists()
    with dm.download("https://data.test/a.zip", cache_dir=tmp_path) as cached:
        assert cached == tmp_path / "a.zip"
    assert cached.exists()


def test_download_missing_file_raises_not_found() -> None:
    dm = _client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(SourceNotFound), dm.download("https://data.test/none.zip"):
        pass


def test_set_ids_for_drug_follows_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200, json={"data": [{"setid": SET_A}], "metadata": {"next_page": 2}}
            )
        return httpx.Response(
            200, json={"data": [{"setid": SET_B}], "metadata": {"next_page": "null"}}
        )

    dm = _client(httpx.MockTransport(handler))
    assert dm.set_ids_for_drug("testamol", limit=5) == [SET_A, SET_B]


def test_spl_document_and_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pillmark.sources.time.sleep", lambda _: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        assert request.url.path.endswith(f"/spls/{SET_A}.xml")
        return httpx.Response(200, content=b"<document/>")

    doc = _client(httpx.MockTransport(handler)).spl_document(SET_A)
    assert doc.xml == b"<document/>"
    assert calls["n"] == 2
