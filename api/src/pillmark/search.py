"""Pill search: turn what someone sees into a ranked SQL query.

Imprint matches are ranked in tiers, best first:

==== ===================================================================
1.00 same characters (``"ip 204"`` = ``"IP;204"``)
0.97 same tokens in another order (``"204 IP"``)
0.90 every typed token is on the pill (``"M"`` finds ``"M;367"``)
0.88 same after folding look-alikes (``"1P2O4"`` finds ``"IP;204"``)
0.85 pill imprint starts with what was typed
0.75 pill imprint contains what was typed
0.65 one character off (``"M357"`` finds ``"M367"``)
<0.6 trigram similarity
==== ===================================================================

Pills that are the same physical product sold by several labelers share a
fingerprint; by default only the group's primary row is returned, with the group
size, so twenty repackagers of one tablet take one result slot. Group sizes and
primary rows are kept up to date by the importer (see ``store.refresh_groups``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from psycopg import sql

from pillmark.imprint import fold, parse_imprint

MAX_LIMIT = 100


@dataclass(slots=True)
class SearchQuery:
    imprint: str | None = None
    colors: list[str] = field(default_factory=list)
    shape: str | None = None
    size_mm: float | None = None
    size_tolerance: float = 1.0
    score: int | None = None
    name: str | None = None
    has_imprint: bool | None = None
    fuzzy_name: bool = False
    include_discontinued: bool = True
    group: bool = True
    limit: int = 24
    offset: int = 0

    @property
    def imprint_key(self) -> str:
        return parse_imprint(self.imprint).key

    def is_empty(self) -> bool:
        return not (
            self.imprint_key
            or self.colors
            or self.shape
            or self.size_mm is not None
            or self.score is not None
            or (self.name and self.name.strip())
            or self.has_imprint is not None
        )


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_IMPRINT_SCORE = """
CASE
    WHEN p.imprint_key = %(k)s THEN 1.0
    WHEN p.imprint_tokens @> %(toks)s::text[] AND p.imprint_tokens <@ %(toks)s::text[] THEN 0.97
    WHEN p.imprint_tokens @> %(toks)s::text[] THEN 0.90
    WHEN p.imprint_fold = %(f)s THEN 0.88
    WHEN p.imprint_key LIKE %(k_prefix)s THEN 0.85
    WHEN p.imprint_key LIKE %(k_contains)s OR p.imprint_fold LIKE %(f_contains)s THEN 0.75
    WHEN length(%(k)s) >= 4 AND levenshtein_less_equal(p.imprint_key, %(k)s, 1) <= 1 THEN 0.65
    ELSE 0.6 * similarity(p.imprint_key, %(k)s)
END
"""

_IMPRINT_MATCH = """
(
    p.imprint_key = %(k)s
    OR p.imprint_tokens @> %(toks)s::text[]
    OR p.imprint_fold = %(f)s
    OR p.imprint_key LIKE %(k_contains)s
    OR p.imprint_fold LIKE %(f_contains)s
    OR (length(%(k)s) >= 3 AND p.imprint_key %% %(k)s)
    OR (length(%(k)s) >= 4 AND levenshtein_less_equal(p.imprint_key, %(k)s, 1) <= 1)
)
"""

# Name search: every word must appear (indexed substring match). If that finds nothing,
# the API retries with ``fuzzy_name`` for typos such as "atorvastin".
_NAME_FUZZY_MATCH = "(%(name)s <%% p.search_text)"
_NAME_FUZZY_SCORE = "word_similarity(%(name)s, p.search_text)"

_COLUMNS = """
p.id, p.set_id, p.product_code, p.part, p.name, p.generic_name, p.dosage_form, p.route,
p.strength, p.ingredients, p.imprint, p.imprint_raw, p.imprint_sides, p.colors, p.shape,
p.size_mm, p.score, p.has_symbol, p.pill_image, p.label_image, p.dea_schedule, p.marketed,
p.marketing_start, p.marketing_end, p.packages, p.fingerprint, p.group_size,
l.labeler, l.effective_date, l.version, l.kind, l.title
"""


def build_search(query: SearchQuery) -> tuple[sql.SQL, dict[str, Any]]:
    """SQL and parameters for a search; each row also has ``total`` and ``group_size``."""
    params: dict[str, Any] = {
        "limit": max(1, min(query.limit, MAX_LIMIT)),
        "offset": max(0, query.offset),
    }
    where: list[str] = []
    score_terms: list[str] = []

    imprint = parse_imprint(query.imprint)
    if imprint.key:
        params.update(
            k=imprint.key,
            toks=list(imprint.tokens),
            f=imprint.fold,
            k_prefix=imprint.key + "%",
            k_contains="%" + imprint.key + "%",
            f_contains="%" + fold(imprint.key) + "%",
        )
        where.append(_IMPRINT_MATCH)
        score_terms.append(_IMPRINT_SCORE)

    if query.has_imprint is True:
        where.append("p.imprint_key <> ''")
    elif query.has_imprint is False:
        where.append("p.imprint_key = ''")

    if query.colors:
        params["colors"] = sorted(set(query.colors))
        where.append("p.colors @> %(colors)s::text[]")
    if query.shape:
        params["shape"] = query.shape
        where.append("p.shape = %(shape)s")
    if query.size_mm is not None:
        tolerance = max(0.0, query.size_tolerance)
        params["size_lo"] = query.size_mm - tolerance
        params["size_hi"] = query.size_mm + tolerance
        where.append("p.size_mm BETWEEN %(size_lo)s AND %(size_hi)s")
    if query.score is not None:
        params["score"] = query.score
        where.append("p.score = %(score)s")

    words = (query.name or "").lower().split()
    if words:
        params["name"] = " ".join(words)
        if query.fuzzy_name:
            where.append(_NAME_FUZZY_MATCH)
            score_terms.append(f"(0.5 + 0.5 * {_NAME_FUZZY_SCORE})")
        else:
            for i, word in enumerate(words[:8]):
                params[f"w{i}"] = "%" + _like_escape(word) + "%"
                where.append(f"p.search_text LIKE %(w{i})s")

    if not query.include_discontinued:
        where.append("p.marketed")

    score_sql = " * ".join(f"({t})" for t in score_terms) if score_terms else "1.0"
    where_sql = " AND ".join(where) if where else "TRUE"
    order_sql = "match_score DESC, marketed DESC, group_size DESC, name NULLS LAST, id"

    if query.group and words:
        # Repackagers may list the same pill under different names and labelers, so
        # a name search matches any member of a group and then keeps one row per group.
        text = f"""
WITH matches AS (
    SELECT {_COLUMNS}, ({score_sql})::real AS match_score,
        row_number() OVER (
            PARTITION BY p.fingerprint ORDER BY p.is_primary DESC, p.id
        ) AS group_rank
    FROM pills p
    JOIN labels l ON l.set_id = p.set_id
    WHERE {where_sql}
)
SELECT m.*, count(*) OVER () AS total
FROM matches m
WHERE m.group_rank = 1
ORDER BY {order_sql}
LIMIT %(limit)s OFFSET %(offset)s
"""
    else:
        # Every other filter is part of the fingerprint, so filtering on the group's
        # primary row is exact.
        primary = "p.is_primary AND " if query.group else ""
        text = f"""
SELECT {_COLUMNS}, ({score_sql})::real AS match_score, count(*) OVER () AS total
FROM pills p
JOIN labels l ON l.set_id = p.set_id
WHERE {primary}{where_sql}
ORDER BY {order_sql}
LIMIT %(limit)s OFFSET %(offset)s
"""
    # Every value above is a fixed SQL fragment; user input only travels in ``params``.
    return sql.SQL(text), params


def build_similar(pill_id: int, limit: int = 100) -> tuple[sql.SQL, dict[str, Any]]:
    """Other labelers' listings of the same physical pill."""
    text = f"""
SELECT {_COLUMNS}, 1.0::real AS match_score, 0 AS total
FROM pills p
JOIN labels l ON l.set_id = p.set_id
WHERE p.fingerprint = (SELECT fingerprint FROM pills WHERE id = %(id)s)
  AND p.id <> %(id)s
ORDER BY p.marketed DESC, l.effective_date DESC NULLS LAST, p.id
LIMIT %(limit)s
"""
    return sql.SQL(text), {"id": pill_id, "limit": limit}


def build_get(pill_id: int) -> tuple[sql.SQL, dict[str, Any]]:
    text = f"""
SELECT {_COLUMNS}, 1.0::real AS match_score, l.label_images, l.document_id
FROM pills p
JOIN labels l ON l.set_id = p.set_id
WHERE p.id = %(id)s
"""
    return sql.SQL(text), {"id": pill_id}
