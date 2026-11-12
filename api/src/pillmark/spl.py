"""Parse FDA Structured Product Labeling (SPL) XML into pills.

An SPL document is one version of one drug label. Its "SPL product data elements"
section (LOINC ``48780-1``) lists every product, and each solid oral product
carries the physical characteristics Pillmark needs:

========== ================================ =========================
Code       Meaning                          Value type
========== ================================ =========================
SPLCOLOR   color, may repeat (two-tone)     CE (NCI code)
SPLSHAPE   shape                            CE (NCI code)
SPLIMPRINT imprint, ``;`` between sides     ST
SPLSIZE    longest dimension                PQ (mm)
SPLSCORE   pieces the score breaks it into  INT
SPLSYMBOL  imprint includes a logo          BL
SPLIMAGE   photo of the pill                ED (file name)
========== ================================ =========================

Kits (for example a birth control pack) list each pill as a ``part`` with its own
characteristics. The package label photo comes from the "principal display panel"
section (LOINC ``51945-4``); it is matched to products by the NDC printed next to it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date

from lxml import etree

from pillmark.imprint import Imprint, parse_imprint
from pillmark.vocab import color_key, shape_key

V3 = "urn:hl7-org:v3"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
NS = {"v3": V3}

NDC_SYSTEM = "2.16.840.1.113883.6.69"
PRODUCT_SECTION = "48780-1"
PRINCIPAL_DISPLAY_PANEL = "51945-4"

DOC_KINDS = {
    "34391-3": "rx",  # HUMAN PRESCRIPTION DRUG LABEL
    "34390-5": "otc",  # HUMAN OTC DRUG LABEL
    "45129-4": "rx",  # HUMAN PRESCRIPTION DRUG LABEL WITH HIGHLIGHTS (legacy)
}

ACTIVE_CLASSES = frozenset({"ACTIB", "ACTIM", "ACTIR"})
SOLID_FORM_RE = re.compile(r"TABLET|CAPSULE|CAPLET|PILL|LOZENGE|TROCHE|WAFER", re.IGNORECASE)
IMAGE_RE = re.compile(r"\.(jpe?g|png|gif)$", re.IGNORECASE)
NDC_RE = re.compile(r"(?<!\d)(\d{4,5})-(\d{3,4})(?:-(\d{1,2}))?(?!\d)")

_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=True,
    remove_comments=True,
    remove_pis=True,
)


_BR = f"{{{V3}}}br"


class SPLParseError(ValueError):
    """The document is not an SPL file Pillmark can read."""


@dataclass(frozen=True, slots=True)
class Ingredient:
    name: str
    strength: str | None = None
    unii: str | None = None


@dataclass(slots=True)
class Pill:
    product_code: str | None
    part: int
    name: str | None
    generic_name: str | None
    dosage_form: str | None
    route: str | None
    strength: str | None
    ingredients: list[Ingredient]
    imprint: Imprint
    colors: tuple[str, ...]
    shape: str | None
    size_mm: float | None
    score: int | None
    has_symbol: bool
    pill_image: str | None
    label_image: str | None
    dea_schedule: str | None
    marketed: bool
    marketing_start: date | None
    marketing_end: date | None
    packages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Label:
    set_id: str
    document_id: str
    version: int
    effective_date: date | None
    title: str | None
    labeler: str | None
    kind: str
    pills: list[Pill]
    label_images: list[str]


# --------------------------------------------------------------------------- helpers


def _q(tag: str) -> str:
    return f"{{{V3}}}{tag}"


def _children(el: etree._Element, tag: str) -> Iterator[etree._Element]:
    yield from el.iterfind(f"v3:{tag}", NS)


def _child(el: etree._Element | None, path: str) -> etree._Element | None:
    if el is None:
        return None
    return el.find(path, NS)


def _attr(el: etree._Element | None, path: str, name: str) -> str | None:
    node = _child(el, path) if path else el
    if node is None:
        return None
    value = node.get(name)
    return value.strip() if value else None


def _text(el: etree._Element | None) -> str | None:
    """Element text with whitespace collapsed; ``<br/>`` counts as a space."""
    if el is None:
        return None
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if child.tag == _BR:
                parts.append(" ")
            elif isinstance(child.tag, str):
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(el)
    text = " ".join("".join(parts).split())
    return text or None


def _hl7_date(value: str | None) -> date | None:
    if not value or len(value) < 8 or not value[:8].isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return None


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _fmt_number(value: float) -> str:
    return f"{value:g}"


def _quantity(q: etree._Element | None) -> str | None:
    """Format an SPL ``quantity`` (numerator over denominator) as ``"500 mg"``."""
    if q is None:
        return None
    num = _child(q, "v3:numerator")
    if num is None:
        return None
    value, unit = _number(num.get("value")), (num.get("unit") or "").strip()
    if value is None:
        return None
    text = _fmt_number(value)
    if unit and unit != "1":
        text += f" {unit}"
    den = _child(q, "v3:denominator")
    if den is not None:
        dval, dunit = _number(den.get("value")), (den.get("unit") or "").strip()
        if dval is not None and (dval != 1 or dunit not in ("", "1")):
            per = _fmt_number(dval) if dval != 1 else ""
            per_unit = dunit if dunit != "1" else ""
            text += "/" + " ".join(p for p in (per, per_unit) if p)
    return text


def _ingredients(product: etree._Element) -> list[Ingredient]:
    found: list[Ingredient] = []
    for ing in _children(product, "ingredient"):
        if ing.get("classCode") not in ACTIVE_CLASSES:
            continue
        substance = _child(ing, "v3:ingredientSubstance")
        name = _text(_child(substance, "v3:name"))
        if name:
            found.append(
                Ingredient(
                    name=name,
                    strength=_quantity(_child(ing, "v3:quantity")),
                    unii=_attr(substance, "v3:code", "code"),
                )
            )
    # Pre-2009 SPL used <activeIngredient>.
    for ing in _children(product, "activeIngredient"):
        substance = _child(ing, "v3:activeIngredientSubstance")
        name = _text(_child(substance, "v3:name"))
        if name:
            found.append(
                Ingredient(
                    name=name,
                    strength=_quantity(_child(ing, "v3:quantity")),
                    unii=_attr(substance, "v3:code", "code"),
                )
            )
    return found


def _strength(ingredients: list[Ingredient]) -> str | None:
    parts = [i.strength for i in ingredients if i.strength]
    return " / ".join(parts) if parts else None


def _product_code(product: etree._Element) -> str | None:
    for code in _children(product, "code"):
        if code.get("codeSystem") == NDC_SYSTEM and code.get("code"):
            return code.get("code")
    return None


def _packages(product: etree._Element) -> list[str]:
    codes: list[str] = []
    for el in product.iterfind(".//v3:containerPackagedProduct/v3:code", NS):
        if el.get("codeSystem") == NDC_SYSTEM and el.get("code"):
            code = el.get("code", "")
            if code not in codes:
                codes.append(code)
    return codes


@dataclass(slots=True)
class _Traits:
    colors: list[str] = field(default_factory=list)
    shape: str | None = None
    imprint: str | None = None
    size_mm: float | None = None
    score: int | None = None
    has_symbol: bool = False
    image: str | None = None


def _traits(container: etree._Element) -> _Traits:
    traits = _Traits()
    for subject in _children(container, "subjectOf"):
        ch = _child(subject, "v3:characteristic")
        if ch is None:
            continue
        code = _attr(ch, "v3:code", "code")
        value = _child(ch, "v3:value")
        if code is None or value is None:
            continue
        if code == "SPLCOLOR":
            key = color_key(value.get("code"), value.get("displayName"))
            if key and key not in traits.colors:
                traits.colors.append(key)
        elif code == "SPLSHAPE":
            traits.shape = shape_key(value.get("code"), value.get("displayName"))
        elif code == "SPLIMPRINT":
            traits.imprint = _text(value)
        elif code == "SPLSIZE":
            size = _number(value.get("value"))
            unit = (value.get("unit") or "mm").lower()
            if size is not None:
                traits.size_mm = size * 10 if unit == "cm" else size
        elif code == "SPLSCORE":
            score = _number(value.get("value"))
            traits.score = int(score) if score is not None else None
        elif code == "SPLSYMBOL":
            traits.has_symbol = (value.get("value") or "").lower() == "true"
        elif code == "SPLIMAGE":
            ref = _attr(value, "v3:reference", "value")
            if ref and IMAGE_RE.search(ref):
                traits.image = ref
    return traits


def _marketing(container: etree._Element) -> tuple[bool, date | None, date | None]:
    act = _child(container, "v3:subjectOf/v3:marketingAct")
    if act is None:
        return True, None, None
    status = _attr(act, "v3:statusCode", "code")
    start = _hl7_date(_attr(act, "v3:effectiveTime/v3:low", "value"))
    end = _hl7_date(_attr(act, "v3:effectiveTime/v3:high", "value"))
    return status != "completed", start, end


def _dea_schedule(container: etree._Element) -> str | None:
    for policy in container.iterfind("v3:subjectOf/v3:policy", NS):
        if policy.get("classCode") == "DEADrugSchedule":
            name = _attr(policy, "v3:code", "displayName")
            if name:
                return name
    return None


def _route(container: etree._Element) -> str | None:
    return _attr(container, "v3:consumedIn/v3:substanceAdministration/v3:routeCode", "displayName")


#: Smallest plausible sizes. Some labels put a capsule's size number ("2") in SPLSIZE.
MIN_CAPSULE_MM = 8.0
MIN_TABLET_MM = 2.0


def _plausible_size(size: float | None, form: str | None) -> float | None:
    if size is None:
        return None
    upper = (form or "").upper()
    is_capsule = "CAPSULE" in upper and "TABLET" not in upper
    if size < (MIN_CAPSULE_MM if is_capsule else MIN_TABLET_MM) or size > 60:
        return None
    return size


def _is_pill(form: str | None, traits: _Traits) -> bool:
    if not (traits.imprint or traits.shape):
        return False
    return form is None or bool(SOLID_FORM_RE.search(form))


def _make_pill(
    *,
    product: etree._Element,
    container: etree._Element,
    traits: _Traits,
    product_code: str | None,
    part: int,
    packages: list[str],
    marketing: tuple[bool, date | None, date | None],
    dea: str | None,
    route: str | None,
) -> Pill:
    ingredients = _ingredients(product)
    generic = _text(_child(product, "v3:asEntityWithGeneric/v3:genericMedicine/v3:name"))
    form = _attr(product, "v3:formCode", "displayName")
    return Pill(
        product_code=product_code,
        part=part,
        name=_text(_child(product, "v3:name")),
        generic_name=generic,
        dosage_form=form,
        route=route,
        strength=_strength(ingredients),
        ingredients=ingredients,
        imprint=parse_imprint(traits.imprint),
        colors=tuple(traits.colors),
        shape=traits.shape,
        size_mm=_plausible_size(traits.size_mm, form),
        score=traits.score,
        has_symbol=traits.has_symbol,
        pill_image=traits.image,
        label_image=None,
        dea_schedule=dea,
        marketed=marketing[0],
        marketing_start=marketing[1],
        marketing_end=marketing[2],
        packages=packages,
    )


def _products(root: etree._Element) -> Iterator[Pill]:
    for section in root.iter(_q("section")):
        if _attr(section, "v3:code", "code") != PRODUCT_SECTION:
            continue
        for outer in section.iterfind("v3:subject/v3:manufacturedProduct", NS):
            inner = _child(outer, "v3:manufacturedProduct")
            if inner is None:
                inner = _child(outer, "v3:manufacturedMedicine")
            if inner is None:
                continue
            code = _product_code(inner)
            packages = _packages(inner)
            marketing = _marketing(outer)
            dea = _dea_schedule(outer)
            route = _route(outer)

            traits = _traits(outer)
            form = _attr(inner, "v3:formCode", "displayName")
            if _is_pill(form, traits):
                yield _make_pill(
                    product=inner,
                    container=outer,
                    traits=traits,
                    product_code=code,
                    part=0,
                    packages=packages,
                    marketing=marketing,
                    dea=dea,
                    route=route,
                )

            for index, part in enumerate(_children(inner, "part"), start=1):
                part_product = _child(part, "v3:partProduct")
                if part_product is None:
                    continue
                part_traits = _traits(part)
                part_form = _attr(part_product, "v3:formCode", "displayName")
                if not _is_pill(part_form, part_traits):
                    continue
                has_own_marketing = _child(part, "v3:subjectOf/v3:marketingAct") is not None
                yield _make_pill(
                    product=part_product,
                    container=part,
                    traits=part_traits,
                    product_code=_product_code(part_product) or code,
                    part=index,
                    packages=packages,
                    marketing=_marketing(part) if has_own_marketing else marketing,
                    dea=_dea_schedule(part) or dea,
                    route=_route(part) or route,
                )


# ------------------------------------------------------------------ label photo matching


@dataclass(slots=True)
class _PanelImage:
    file: str
    context: str


def _media_index(root: etree._Element) -> dict[str, str]:
    """Map ``observationMedia/@ID`` to the image file it references."""
    index: dict[str, str] = {}
    for media in root.iter(_q("observationMedia")):
        media_id = media.get("ID")
        ref = _attr(media, "v3:value/v3:reference", "value")
        if media_id and ref and IMAGE_RE.search(ref):
            index[media_id] = ref
    return index


def _panel_images(root: etree._Element, media: dict[str, str]) -> list[_PanelImage]:
    """Images in principal display panel sections, with the text printed around them."""
    found: list[_PanelImage] = []
    seen: set[str] = set()
    for section in root.iter(_q("section")):
        if _attr(section, "v3:code", "code") != PRINCIPAL_DISPLAY_PANEL:
            continue
        buffer: list[str] = []
        title = _text(_child(section, "v3:title")) or ""
        for el in section.iter():
            if (
                not isinstance(el.tag, str)
                or next(el.iterancestors(_q("observationMedia")), None) is not None
            ):
                continue
            if el.tag == _q("renderMultiMedia"):
                file = media.get(el.get("referencedObject") or "")
                if file and file not in seen:
                    seen.add(file)
                    found.append(_PanelImage(file, " ".join([title, *buffer])))
                buffer = []
            elif el.tag == _q("observationMedia"):
                continue
            else:
                if el.text and el.tag != _q("reference"):
                    buffer.append(el.text)
                if el.tail:
                    buffer.append(el.tail)
        # Images referenced only from components (no renderMultiMedia) still count.
        for media_el in section.iter(_q("observationMedia")):
            ref = _attr(media_el, "v3:value/v3:reference", "value")
            if ref and IMAGE_RE.search(ref) and ref not in seen:
                seen.add(ref)
                found.append(_PanelImage(ref, title))
    return found


def _ndc_pairs(text: str) -> set[tuple[int, int]]:
    return {(int(m.group(1)), int(m.group(2))) for m in NDC_RE.finditer(text)}


def _code_pair(product_code: str | None) -> tuple[int, int] | None:
    if not product_code:
        return None
    m = NDC_RE.fullmatch(product_code) or re.fullmatch(r"(\d{4,5})-(\d{3,4})", product_code)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _strength_numbers(strength: str | None) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", strength or "")


def _assign_label_images(pills: list[Pill], panels: list[_PanelImage]) -> None:
    if not panels:
        return
    pairs = [_ndc_pairs(p.context) for p in panels]
    for pill in pills:
        target = _code_pair(pill.product_code)
        chosen: str | None = None
        if target:
            for panel, found in zip(panels, pairs, strict=True):
                if target in found:
                    chosen = panel.file
                    break
        if chosen is None:
            numbers = _strength_numbers(pill.strength)
            if numbers:
                for panel in panels:
                    words = set(re.findall(r"\d+(?:\.\d+)?", panel.context))
                    if all(n in words for n in numbers):
                        chosen = panel.file
                        break
        pill.label_image = chosen or panels[0].file


# ------------------------------------------------------------------------- public API


def parse_spl(xml: bytes) -> Label:
    """Parse one SPL XML document."""
    try:
        root = etree.fromstring(xml, parser=_PARSER)
    except etree.XMLSyntaxError as exc:
        raise SPLParseError(f"not well-formed XML: {exc}") from exc
    if root.tag != _q("document"):
        raise SPLParseError(f"root element is {root.tag!r}, expected an HL7 v3 document")

    set_id = _attr(root, "v3:setId", "root")
    document_id = _attr(root, "v3:id", "root")
    if not set_id or not document_id:
        raise SPLParseError("document has no setId or id")
    version_text = _attr(root, "v3:versionNumber", "value") or "1"
    try:
        version = int(version_text)
    except ValueError:
        version = 1

    pills = list(_products(root))
    panels = _panel_images(root, _media_index(root))
    _assign_label_images(pills, panels)

    return Label(
        set_id=set_id.lower(),
        document_id=document_id.lower(),
        version=version,
        effective_date=_hl7_date(_attr(root, "v3:effectiveTime", "value")),
        title=_text(_child(root, "v3:title")),
        labeler=_text(
            _child(root, "v3:author/v3:assignedEntity/v3:representedOrganization/v3:name")
        ),
        kind=DOC_KINDS.get(_attr(root, "v3:code", "code") or "", "other"),
        pills=pills,
        label_images=[p.file for p in panels],
    )


def iter_pills(labels: Iterable[Label]) -> Iterator[tuple[Label, Pill]]:
    for label in labels:
        for pill in label.pills:
            yield label, pill
