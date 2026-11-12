"""The web app keeps its own copy of the vocabulary for drawing; keep them identical."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pillmark.vocab import COLORS, SHAPES

WEB_VOCAB = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "vocab.ts"


@pytest.fixture(scope="module")
def source() -> str:
    if not WEB_VOCAB.exists():
        pytest.skip("web app not checked out next to the API")
    return WEB_VOCAB.read_text("utf-8")


def test_colors_match(source: str) -> None:
    found = re.findall(
        r"\{ key: '([a-z-]+)', label: '([^']+)', hex: '(#[0-9A-Fa-f]{6})' \}", source
    )
    assert [(k, h.upper()) for k, _, h in found] == [(c.key, c.hex.upper()) for c in COLORS]


def test_shapes_match(source: str) -> None:
    found = re.findall(r"\{ key: '([a-z-]+)', label: '[^']+', hint: '[^']+' \}", source)
    assert sorted(found) == sorted(s.key for s in SHAPES)
