"""Imprint normalization.

Labels record imprints like ``"M;A;10"`` or ``"IP 204"``, where ``;`` separates the
text on different sides or lines. People type them every which way: ``"ip204"``,
``"204 IP"``, ``"MA10"``. Every imprint is reduced to three forms that are cheap
to index and compare in Postgres:

``tokens``
    Upper-case alphanumeric runs, in order: ``["M", "A", "10"]``. Lets a search
    match regardless of which side the user read first.
``key``
    The tokens joined with no separator: ``"MA10"``. Lets ``"IP 204"`` match
    ``"IP204"`` and drives the trigram index.
``fold``
    The key with characters people confuse on tiny pills folded together
    (``O`` and ``0``; ``I``, ``L`` and ``1``). Used as a lower-ranked match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[A-Z0-9]+")
_FOLD = str.maketrans({"O": "0", "I": "1", "L": "1"})

# Words that labels use to describe a debossed logo rather than literal text.
_LOGO_WORDS = frozenset({"LOGO", "SYMBOL", "DESIGN", "IMAGE", "EMBLEM"})


@dataclass(frozen=True, slots=True)
class Imprint:
    raw: str
    display: str
    sides: tuple[str, ...]
    tokens: tuple[str, ...]
    key: str
    fold: str

    @property
    def is_empty(self) -> bool:
        return not self.key


def _clean_side(side: str) -> str:
    return " ".join(side.split())


def tokens_of(text: str) -> tuple[str, ...]:
    """Upper-case alphanumeric tokens, ignoring logo placeholder words."""
    return tuple(t for t in _TOKEN_RE.findall(text.upper()) if t not in _LOGO_WORDS)


def fold(key: str) -> str:
    return key.translate(_FOLD)


def parse_imprint(raw: str | None) -> Imprint:
    """Normalize an imprint string from a label or a user query."""
    raw = (raw or "").strip()
    sides = tuple(s for s in (_clean_side(p) for p in raw.split(";")) if s)
    tokens = tokens_of(raw)
    key = "".join(tokens)
    return Imprint(
        raw=raw,
        display=" ".join(sides),
        sides=sides,
        tokens=tokens,
        key=key,
        fold=fold(key),
    )
