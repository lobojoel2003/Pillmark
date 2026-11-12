"""Where SPL documents come from.

DailyMed publishes three kinds of bulk files on ``dailymed-data.nlm.nih.gov``:

* full releases, split into parts (``dm_spl_release_human_rx_part1.zip`` ...),
* monthly and weekly updates,
* a daily update (``dm_spl_daily_update_MMDDYYYY.zip``), which the nightly job reads.

All of them are a zip of folders (``prescription/``, ``otc/``, ``animal/`` ...) that
hold one inner zip per label. Each inner zip has the SPL XML and its images. A daily
update also lists the label versions it replaces or removes in ``files_deleted.txt``.

For development there is also the DailyMed web service, which can look labels up by
drug name or set id.
"""

from __future__ import annotations

import io
import logging
import re
import shutil
import tempfile
import time
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import IO, Any

import httpx

from pillmark.settings import Settings, get_settings

log = logging.getLogger(__name__)

#: Top-level folders in DailyMed bulk zips that hold human drug labels.
HUMAN_FOLDERS: frozenset[str] = frozenset({"prescription", "otc"})

FULL_RELEASE_PARTS: dict[str, int] = {"human_rx": 6, "human_otc": 12}

MAX_INNER_ZIP_BYTES = 256 * 1024 * 1024
MAX_XML_BYTES = 64 * 1024 * 1024

_SETID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """One SPL XML document and the image files packaged with it."""

    name: str
    xml: bytes
    images: tuple[str, ...] = ()


def set_id_from_name(name: str) -> str | None:
    match = _SETID_RE.search(name)
    return match.group(1).lower() if match else None


# ---------------------------------------------------------------------------- archives


def _top_folder(name: str) -> str:
    return name.split("/", 1)[0] if "/" in name else ""


def _documents_in_zip(zf: zipfile.ZipFile, label: str) -> Iterator[SourceDocument]:
    names = zf.namelist()
    images = tuple(
        Path(n).name for n in names if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
    )
    for info in zf.infolist():
        lower = info.filename.lower()
        if lower.endswith(".xml"):
            if info.file_size > MAX_XML_BYTES:
                log.warning("skipping oversized XML %s in %s", info.filename, label)
                continue
            yield SourceDocument(name=f"{label}:{info.filename}", xml=zf.read(info), images=images)
        elif lower.endswith(".zip"):
            if info.file_size > MAX_INNER_ZIP_BYTES:
                log.warning("skipping oversized inner zip %s in %s", info.filename, label)
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                    yield from _documents_in_zip(inner, info.filename)
            except zipfile.BadZipFile:
                log.warning("skipping corrupt inner zip %s in %s", info.filename, label)


def iter_archive(
    source: str | Path | IO[bytes], folders: Iterable[str] | None = HUMAN_FOLDERS
) -> Iterator[SourceDocument]:
    """Yield every SPL document in a DailyMed bulk zip.

    ``folders`` limits which top-level folders are read; ``None`` reads all of them.
    Archives without folders (a zip of label zips, or a single label zip) are read whole.
    """
    wanted = frozenset(folders) if folders is not None else None
    with zipfile.ZipFile(source) as zf:
        has_folders = any("/" in n for n in zf.namelist())
        for info in zf.infolist():
            if info.is_dir():
                continue
            if wanted is not None and has_folders and _top_folder(info.filename) not in wanted:
                continue
            lower = info.filename.lower()
            if lower.endswith(".zip"):
                if info.file_size > MAX_INNER_ZIP_BYTES:
                    log.warning("skipping oversized inner zip %s", info.filename)
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                        yield from _documents_in_zip(inner, info.filename)
                except zipfile.BadZipFile:
                    log.warning("skipping corrupt inner zip %s", info.filename)
            elif lower.endswith(".xml") and info.file_size <= MAX_XML_BYTES:
                images = tuple(
                    Path(n).name
                    for n in zf.namelist()
                    if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
                )
                yield SourceDocument(name=info.filename, xml=zf.read(info), images=images)


def removed_set_ids(source: str | Path | IO[bytes]) -> set[str]:
    """Set ids a DailyMed update removes outright (deleted and not re-added)."""
    with zipfile.ZipFile(source) as zf:
        names = set(zf.namelist())

        def read(name: str) -> list[str]:
            if name not in names:
                return []
            return zf.read(name).decode("utf-8", "replace").splitlines()

        added = {s for s in map(set_id_from_name, read("files_added.txt")) if s}
        deleted = {s for s in map(set_id_from_name, read("files_deleted.txt")) if s}
    return deleted - added


# ------------------------------------------------------------------------------ remote


class SourceNotFound(LookupError):
    """DailyMed has no file at that address (for example, no update for that day)."""


class DailyMed:
    """Small client for DailyMed bulk files and web services."""

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(self.settings.http_timeout, connect=20.0),
            headers={"User-Agent": self.settings.user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DailyMed:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # urls ------------------------------------------------------------------------

    def daily_url(self, day: date) -> str:
        return f"{self.settings.dailymed_data_base}/dm_spl_daily_update_{day:%m%d%Y}.zip"

    def full_release_urls(self, kind: str) -> list[str]:
        if kind not in FULL_RELEASE_PARTS:
            raise ValueError(f"unknown release {kind!r}; choose from {sorted(FULL_RELEASE_PARTS)}")
        base = self.settings.dailymed_data_base
        return [
            f"{base}/dm_spl_release_{kind}_part{n}.zip"
            for n in range(1, FULL_RELEASE_PARTS[kind] + 1)
        ]

    # requests --------------------------------------------------------------------

    def _get(self, url: str, **params: Any) -> httpx.Response:
        delay = 2.0
        for attempt in range(1, 5):
            try:
                response = self._client.get(url, params=params or None)
            except httpx.TransportError as exc:
                if attempt == 4:
                    raise
                log.warning("GET %s failed (%s); retrying in %.0fs", url, exc, delay)
            else:
                if response.status_code == 404:
                    raise SourceNotFound(url)
                if response.status_code < 500 and response.status_code != 429:
                    response.raise_for_status()
                    return response
                if attempt == 4:
                    response.raise_for_status()
                log.warning("GET %s returned %s; retrying", url, response.status_code)
            time.sleep(delay)
            delay *= 2
        raise RuntimeError("unreachable")  # pragma: no cover

    @contextmanager
    def download(self, url: str, cache_dir: Path | None = None) -> Iterator[Path]:
        """Download ``url`` to a file and yield its path.

        With ``cache_dir`` the file is kept and reused; otherwise it is deleted afterwards.
        """
        name = url.rsplit("/", 1)[-1]
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / name
            if target.exists() and target.stat().st_size > 0:
                log.info("using cached %s", target)
                yield target
                return
        tmpdir = Path(tempfile.mkdtemp(prefix="pillmark-"))
        partial = tmpdir / name
        try:
            log.info("downloading %s", url)
            with self._client.stream("GET", url) as response:
                if response.status_code == 404:
                    raise SourceNotFound(url)
                response.raise_for_status()
                with partial.open("wb") as fh:
                    for chunk in response.iter_bytes(1024 * 1024):
                        fh.write(chunk)
            if cache_dir is not None:
                final = cache_dir / name
                shutil.move(partial, final)
                yield final
            else:
                yield partial
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def set_ids_for_drug(self, drug_name: str, limit: int = 25) -> list[str]:
        """Most recently published set ids whose label matches ``drug_name``."""
        found: list[str] = []
        page = 1
        while len(found) < limit:
            data = self._get(
                f"{self.settings.dailymed_base}/services/v2/spls.json",
                drug_name=drug_name,
                pagesize=min(100, limit),
                page=page,
            ).json()
            rows = data.get("data") or []
            found.extend(r["setid"] for r in rows if r.get("setid") not in found)
            meta = data.get("metadata") or {}
            if not rows or str(meta.get("next_page")) in ("null", "None", ""):
                break
            page += 1
        return found[:limit]

    def spl_document(self, set_id: str) -> SourceDocument:
        """Latest SPL XML for one set id, via the web service."""
        response = self._get(f"{self.settings.dailymed_base}/services/v2/spls/{set_id}.xml")
        return SourceDocument(name=f"setid:{set_id}", xml=response.content)


def image_url(base: str, set_id: str, file: str | None) -> str | None:
    """Public DailyMed URL for an image packaged with a label."""
    if not file:
        return None
    return str(httpx.URL(f"{base}/image.cfm", params={"setid": set_id, "name": file}))
