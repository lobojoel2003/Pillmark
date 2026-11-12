"""Write parsed labels into PostgreSQL."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from pillmark.spl import Label, Pill


class WriteResult(StrEnum):
    UPSERTED = "upserted"
    SKIPPED = "skipped"
    EMPTY = "empty"
    DELETED = "deleted"


def fingerprint(pill: Pill) -> str:
    """Identify the same physical pill across labelers and repackagers.

    Everything a search can filter on is part of the fingerprint, so every member
    of a group matches the same searches as the group's primary row.
    """
    parts = [
        pill.imprint.key,
        pill.shape or "",
        ",".join(sorted(pill.colors)),
        f"{pill.size_mm:g}" if pill.size_mm is not None else "",
        str(pill.score) if pill.score is not None else "",
        (pill.generic_name or pill.name or "").lower().strip(),
        (pill.strength or "").lower().replace(" ", ""),
    ]
    return hashlib.md5("|".join(parts).encode(), usedforsecurity=False).hexdigest()


def search_text(label: Label, pill: Pill) -> str:
    words = [pill.name, pill.generic_name, *(i.name for i in pill.ingredients), label.labeler]
    return " ".join(w.lower() for w in words if w)


_LABEL_SQL = """
INSERT INTO labels (set_id, document_id, version, effective_date, title, labeler, kind,
                    label_images, source, imported_at)
VALUES (%(set_id)s, %(document_id)s, %(version)s, %(effective_date)s, %(title)s,
        %(labeler)s, %(kind)s, %(label_images)s, %(source)s, now())
ON CONFLICT (set_id) DO UPDATE SET
    document_id = EXCLUDED.document_id,
    version = EXCLUDED.version,
    effective_date = EXCLUDED.effective_date,
    title = EXCLUDED.title,
    labeler = EXCLUDED.labeler,
    kind = EXCLUDED.kind,
    label_images = EXCLUDED.label_images,
    source = EXCLUDED.source,
    imported_at = now()
"""

_PILL_SQL = """
INSERT INTO pills (set_id, product_code, part, name, generic_name, dosage_form, route,
                   strength, ingredients, imprint_raw, imprint, imprint_sides, imprint_tokens,
                   imprint_key, imprint_fold, colors, shape, size_mm, score, has_symbol,
                   pill_image, label_image, dea_schedule, marketed, marketing_start,
                   marketing_end, packages, fingerprint, search_text)
VALUES (%(set_id)s, %(product_code)s, %(part)s, %(name)s, %(generic_name)s, %(dosage_form)s,
        %(route)s, %(strength)s, %(ingredients)s, %(imprint_raw)s, %(imprint)s,
        %(imprint_sides)s, %(imprint_tokens)s, %(imprint_key)s, %(imprint_fold)s, %(colors)s,
        %(shape)s, %(size_mm)s, %(score)s, %(has_symbol)s, %(pill_image)s, %(label_image)s,
        %(dea_schedule)s, %(marketed)s, %(marketing_start)s, %(marketing_end)s, %(packages)s,
        %(fingerprint)s, %(search_text)s)
"""


def _pill_row(label: Label, pill: Pill) -> dict[str, Any]:
    return {
        "set_id": label.set_id,
        "product_code": pill.product_code,
        "part": pill.part,
        "name": pill.name,
        "generic_name": pill.generic_name,
        "dosage_form": pill.dosage_form,
        "route": pill.route,
        "strength": pill.strength,
        "ingredients": Jsonb(
            [{"name": i.name, "strength": i.strength, "unii": i.unii} for i in pill.ingredients]
        ),
        "imprint_raw": pill.imprint.raw,
        "imprint": pill.imprint.display,
        "imprint_sides": list(pill.imprint.sides),
        "imprint_tokens": list(pill.imprint.tokens),
        "imprint_key": pill.imprint.key,
        "imprint_fold": pill.imprint.fold,
        "colors": list(pill.colors),
        "shape": pill.shape,
        "size_mm": pill.size_mm,
        "score": pill.score,
        "has_symbol": pill.has_symbol,
        "pill_image": pill.pill_image,
        "label_image": pill.label_image,
        "dea_schedule": pill.dea_schedule,
        "marketed": pill.marketed,
        "marketing_start": pill.marketing_start,
        "marketing_end": pill.marketing_end,
        "packages": pill.packages,
        "fingerprint": fingerprint(pill),
        "search_text": search_text(label, pill),
    }


def _unique_pills(pills: list[Pill]) -> list[Pill]:
    seen: set[tuple[str | None, int]] = set()
    unique: list[Pill] = []
    for pill in pills:
        key = (pill.product_code, pill.part)
        if key not in seen:
            seen.add(key)
            unique.append(pill)
    return unique


def _fingerprints_of(conn: psycopg.Connection[Any], set_ids: list[str]) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT fingerprint FROM pills WHERE set_id = ANY(%s::uuid[])", (set_ids,)
    ).fetchall()
    return {r[0] for r in rows}


def write_label(
    conn: psycopg.Connection[Any],
    label: Label,
    *,
    source: str,
    force: bool = False,
    touched: set[str] | None = None,
) -> tuple[WriteResult, int]:
    """Store a label and its pills, replacing an older version.

    Returns what happened and how many pill rows were written. Labels with no pills
    (liquids, creams, injectables) are not stored; if an older version had pills,
    it is removed. Fingerprints of pills added or removed go into ``touched`` so
    :func:`refresh_groups` can update them; without ``touched`` they are refreshed
    right away.
    """
    batch: set[str] = set()
    result = _write_label(conn, label, source=source, force=force, touched=batch)
    if touched is None:
        refresh_groups(conn, batch)
    else:
        touched |= batch
    return result


def _write_label(
    conn: psycopg.Connection[Any],
    label: Label,
    *,
    source: str,
    force: bool,
    touched: set[str],
) -> tuple[WriteResult, int]:
    row = conn.execute(
        "SELECT version FROM labels WHERE set_id = %s FOR UPDATE", (label.set_id,)
    ).fetchone()
    existing: int | None = row[0] if row else None
    if existing is not None and (
        existing > label.version or (existing == label.version and not force)
    ):
        return WriteResult.SKIPPED, 0

    if existing is not None:
        touched |= _fingerprints_of(conn, [label.set_id])
    pills = _unique_pills(label.pills)
    if not pills:
        if existing is not None:
            conn.execute("DELETE FROM labels WHERE set_id = %s", (label.set_id,))
            return WriteResult.DELETED, 0
        return WriteResult.EMPTY, 0

    conn.execute(
        _LABEL_SQL,
        {
            "set_id": label.set_id,
            "document_id": label.document_id,
            "version": label.version,
            "effective_date": label.effective_date,
            "title": label.title,
            "labeler": label.labeler,
            "kind": label.kind,
            "label_images": label.label_images,
            "source": source,
        },
    )
    conn.execute("DELETE FROM pills WHERE set_id = %s", (label.set_id,))
    rows = [_pill_row(label, p) for p in pills]
    touched |= {r["fingerprint"] for r in rows}
    with conn.cursor() as cur:
        cur.executemany(_PILL_SQL, rows)
    return WriteResult.UPSERTED, len(pills)


def delete_labels(
    conn: psycopg.Connection[Any], set_ids: set[str], touched: set[str] | None = None
) -> int:
    if not set_ids:
        return 0
    ids = sorted(set_ids)
    batch = _fingerprints_of(conn, ids)
    cur = conn.execute("DELETE FROM labels WHERE set_id = ANY(%s::uuid[])", (ids,))
    if touched is None:
        refresh_groups(conn, batch)
    else:
        touched |= batch
    return cur.rowcount


_REFRESH_SQL = """
WITH ranked AS (
    SELECT p.id,
        count(*) OVER (PARTITION BY p.fingerprint) AS n,
        row_number() OVER (
            PARTITION BY p.fingerprint
            ORDER BY (p.pill_image IS NOT NULL) DESC, p.marketed DESC,
                     l.effective_date DESC NULLS LAST, p.id
        ) AS rn
    FROM pills p
    JOIN labels l ON l.set_id = p.set_id
    WHERE {scope}
)
UPDATE pills SET group_size = r.n, is_primary = (r.rn = 1)
FROM ranked r
WHERE pills.id = r.id AND (pills.group_size <> r.n OR pills.is_primary <> (r.rn = 1))
"""


def refresh_groups(conn: psycopg.Connection[Any], fingerprints: set[str] | None = None) -> int:
    """Recompute group sizes and primary rows (all of them when ``fingerprints`` is None)."""
    if fingerprints is not None and not fingerprints:
        return 0
    if fingerprints is None:
        cur = conn.execute(_REFRESH_SQL.format(scope="TRUE").encode())
    else:
        cur = conn.execute(
            _REFRESH_SQL.format(scope="p.fingerprint = ANY(%s)").encode(), (sorted(fingerprints),)
        )
    return cur.rowcount
