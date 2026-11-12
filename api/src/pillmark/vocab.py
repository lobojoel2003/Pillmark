"""Controlled vocabularies used by FDA Structured Product Labeling (SPL).

SPL records pill color and shape as NCI Thesaurus codes. Pillmark stores short,
stable keys (``"white"``, ``"round"``) and maps both the codes and the display
names found in real labels onto them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Color:
    key: str
    label: str
    nci_code: str
    hex: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Shape:
    key: str
    label: str
    nci_code: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


COLORS: tuple[Color, ...] = (
    Color("white", "White", "C48325", "#F6F4EE"),
    Color("yellow", "Yellow", "C48330", "#F2D04B"),
    Color("orange", "Orange", "C48331", "#EE8A3A"),
    Color("red", "Red", "C48326", "#D2453C"),
    Color("pink", "Pink", "C48328", "#F2A0B8"),
    Color("purple", "Purple", "C48327", "#8A63C8"),
    Color("blue", "Blue", "C48333", "#4F86D9"),
    Color("turquoise", "Turquoise", "C48334", "#3FB6B2"),
    Color("green", "Green", "C48329", "#5DAA68"),
    Color("brown", "Brown", "C48332", "#9A6A43"),
    Color("gray", "Gray", "C48324", "#B5B8BD"),
    Color("black", "Black", "C48323", "#2B2B2E"),
)

SHAPES: tuple[Shape, ...] = (
    Shape("round", "Round", "C48348", "A circle seen from above."),
    Shape("oval", "Oval", "C48345", "An ellipse with rounded ends."),
    Shape(
        "capsule",
        "Capsule / oblong",
        "C48336",
        "A long pill with straight sides and round ends. SPL also uses this for oblong tablets.",
    ),
    Shape("rectangle", "Rectangle", "C48347", "Four straight sides, longer than wide."),
    Shape("square", "Square", "C48350", "Four equal sides."),
    Shape("triangle", "Triangle", "C48353", "Three sides."),
    Shape("diamond", "Diamond", "C48338", "A square turned on its corner."),
    Shape("pentagon", "Pentagon", "C48346", "Five sides."),
    Shape("hexagon", "Hexagon", "C48343", "Six sides."),
    Shape("heptagon", "Heptagon", "C48342", "Seven sides."),
    Shape("octagon", "Octagon", "C48344", "Eight sides."),
    Shape("semi-circle", "Half circle", "C48349", "A circle cut in half."),
    Shape("tear", "Teardrop", "C48351", "Round at one end, pointed at the other."),
    Shape("trapezoid", "Trapezoid", "C48352", "Four sides, two of them parallel."),
    Shape("bullet", "Bullet", "C48335", "Flat at one end, rounded at the other."),
    Shape("clover", "Clover", "C48337", "Rounded lobes, like a clover leaf."),
    Shape("gear", "Gear", "C48341", "Notched edges, like a cog."),
    Shape("double-circle", "Double circle", "C48339", "Two overlapping circles."),
    Shape("freeform", "Other shape", "C48340", "Any shape not listed here."),
)

COLOR_KEYS: frozenset[str] = frozenset(c.key for c in COLORS)
SHAPE_KEYS: frozenset[str] = frozenset(s.key for s in SHAPES)

_COLOR_BY_CODE = {c.nci_code: c.key for c in COLORS}
_SHAPE_BY_CODE = {s.nci_code: s.key for s in SHAPES}

_COLOR_ALIASES = {
    "grey": "gray",
    "silver": "gray",
    "tan": "brown",
    "beige": "brown",
    "cream": "white",
    "off-white": "white",
    "off white": "white",
    "clear": "white",
    "transparent": "white",
    "violet": "purple",
    "lavender": "purple",
    "maroon": "red",
    "peach": "orange",
    "aqua": "turquoise",
    "teal": "turquoise",
}

_SHAPE_ALIASES = {
    "oblong": "capsule",
    "caplet": "capsule",
    "circle": "round",
    "circular": "round",
    "elliptical": "oval",
    "ellipse": "oval",
    "half circle": "semi-circle",
    "semicircle": "semi-circle",
    "semi circle": "semi-circle",
    "teardrop": "tear",
    "double circle": "double-circle",
    "free form": "freeform",
    "other": "freeform",
    "heptagon (7 sided)": "heptagon",
    "hexagon (6 sided)": "hexagon",
    "octagon (8 sided)": "octagon",
    "pentagon (5 sided)": "pentagon",
}


def color_key(code: str | None, display_name: str | None = None) -> str | None:
    """Map an SPL color (NCI code and/or display name) to a Pillmark color key."""
    if code and code in _COLOR_BY_CODE:
        return _COLOR_BY_CODE[code]
    if not display_name:
        return None
    name = display_name.strip().lower()
    if name in COLOR_KEYS:
        return name
    return _COLOR_ALIASES.get(name)


def shape_key(code: str | None, display_name: str | None = None) -> str | None:
    """Map an SPL shape (NCI code and/or display name) to a Pillmark shape key."""
    if code and code in _SHAPE_BY_CODE:
        return _SHAPE_BY_CODE[code]
    if not display_name:
        return None
    name = display_name.strip().lower()
    if name in SHAPE_KEYS:
        return name
    if name in _SHAPE_ALIASES:
        return _SHAPE_ALIASES[name]
    first = name.split(" (", 1)[0].replace(" ", "-")
    return first if first in SHAPE_KEYS else None


def normalize_color_param(value: str) -> str | None:
    """Accept a color key, label or alias from an API caller."""
    return color_key(None, value)


def normalize_shape_param(value: str) -> str | None:
    """Accept a shape key, label or alias from an API caller."""
    v = value.strip().lower()
    if v in SHAPE_KEYS:
        return v
    by_label = {s.label.lower(): s.key for s in SHAPES}
    if v in by_label:
        return by_label[v]
    return shape_key(None, v)
