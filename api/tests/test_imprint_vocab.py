from __future__ import annotations

import pytest

from pillmark.imprint import parse_imprint
from pillmark.vocab import (
    COLORS,
    SHAPES,
    color_key,
    normalize_color_param,
    normalize_shape_param,
    shape_key,
)


@pytest.mark.parametrize(
    ("raw", "display", "tokens", "key"),
    [
        ("M;A;10", "M A 10", ("M", "A", "10"), "MA10"),
        ("IP 204", "IP 204", ("IP", "204"), "IP204"),
        ("  ip-204  ", "ip-204", ("IP", "204"), "IP204"),
        ("b;987", "b 987", ("B", "987"), "B987"),
        ("LOGO;5", "LOGO 5", ("5",), "5"),
        ("", "", (), ""),
        (None, "", (), ""),
    ],
)
def test_parse_imprint(raw: str | None, display: str, tokens: tuple[str, ...], key: str) -> None:
    imprint = parse_imprint(raw)
    assert imprint.display == display
    assert imprint.tokens == tokens
    assert imprint.key == key
    assert imprint.is_empty is (key == "")


def test_fold_merges_look_alike_characters() -> None:
    assert parse_imprint("IP 2O4").fold == parse_imprint("1P 204").fold == "1P204"
    assert parse_imprint("L5").fold == "15"


def test_sides_split_on_semicolons() -> None:
    assert parse_imprint("WATSON;3203; ").sides == ("WATSON", "3203")


def test_color_key_by_code_name_and_alias() -> None:
    assert color_key("C48325", "whatever") == "white"
    assert color_key(None, "WHITE") == "white"
    assert color_key(None, "grey") == "gray"
    assert color_key(None, "mauve") is None
    assert color_key(None, None) is None


@pytest.mark.parametrize(
    ("code", "name", "expected"),
    [
        ("C48348", None, "round"),
        (None, "CAPSULE", "capsule"),
        (None, "HEXAGON (6 sided)", "hexagon"),
        (None, "SEMI-CIRCLE", "semi-circle"),
        (None, "DOUBLE CIRCLE", "double-circle"),
        (None, "oblong", "capsule"),
        (None, "blob", None),
    ],
)
def test_shape_key(code: str | None, name: str | None, expected: str | None) -> None:
    assert shape_key(code, name) == expected


def test_api_params_accept_labels_and_aliases() -> None:
    assert normalize_shape_param("Capsule / oblong") == "capsule"
    assert normalize_shape_param("Half circle") == "semi-circle"
    assert normalize_shape_param("ROUND") == "round"
    assert normalize_color_param("Turquoise") == "turquoise"


def test_vocab_is_complete_and_unique() -> None:
    assert len({c.key for c in COLORS}) == len(COLORS) == 12
    assert len({s.key for s in SHAPES}) == len(SHAPES) == 19
    assert all(c.hex.startswith("#") and len(c.hex) == 7 for c in COLORS)
