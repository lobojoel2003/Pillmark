"""Build small but realistic SPL documents for tests.

The structure mirrors real DailyMed files: a product data elements section
(LOINC 48780-1) and a principal display panel section (LOINC 51945-4) whose
images are matched to products by NDC.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

COLOR_CODES = {
    "white": "C48325",
    "yellow": "C48330",
    "orange": "C48331",
    "red": "C48326",
    "pink": "C48328",
    "purple": "C48327",
    "blue": "C48333",
    "turquoise": "C48334",
    "green": "C48329",
    "brown": "C48332",
    "gray": "C48324",
    "black": "C48323",
}
SHAPE_CODES = {
    "round": ("C48348", "ROUND"),
    "oval": ("C48345", "OVAL"),
    "capsule": ("C48336", "CAPSULE"),
    "triangle": ("C48353", "TRIANGLE"),
}


@dataclass
class Product:
    ndc: str = "0000-0001"
    name: str = "Testamol"
    generic: str = "testamol hydrochloride"
    form: str = "TABLET, FILM COATED"
    ingredients: list[tuple[str, str, str]] = field(
        default_factory=lambda: [("TESTAMOL HYDROCHLORIDE", "500", "mg")]
    )
    imprint: str | None = "TM;500"
    colors: list[str] = field(default_factory=lambda: ["white"])
    shape: str | None = "oval"
    size: float | None = 17
    score: int | None = 2
    image: str | None = None
    status: str = "active"
    dea: str | None = None
    parts: list[Product] = field(default_factory=list)


def _characteristics(p: Product) -> str:
    out = []
    for color in p.colors:
        out.append(
            f'<subjectOf><characteristic classCode="OBS"><code code="SPLCOLOR" '
            f'codeSystem="2.16.840.1.113883.1.11.19255"/><value xsi:type="CE" '
            f'code="{COLOR_CODES[color]}" displayName="{color.upper()}" '
            f'codeSystem="2.16.840.1.113883.3.26.1.1"/></characteristic></subjectOf>'
        )
    if p.shape:
        code, name = SHAPE_CODES[p.shape]
        out.append(
            '<subjectOf><characteristic classCode="OBS"><code code="SPLSHAPE"/>'
            f'<value xsi:type="CE" code="{code}" displayName="{name}"/></characteristic>'
            "</subjectOf>"
        )
    if p.size is not None:
        out.append(
            '<subjectOf><characteristic><code code="SPLSIZE"/>'
            f'<value xsi:type="PQ" value="{p.size:g}" unit="mm"/></characteristic></subjectOf>'
        )
    if p.score is not None:
        out.append(
            '<subjectOf><characteristic><code code="SPLSCORE"/>'
            f'<value xsi:type="INT" value="{p.score}"/></characteristic></subjectOf>'
        )
    if p.imprint is not None:
        out.append(
            '<subjectOf><characteristic><code code="SPLIMPRINT"/>'
            f'<value xsi:type="ST">{escape(p.imprint)}</value></characteristic></subjectOf>'
        )
    if p.image:
        out.append(
            '<subjectOf><characteristic><code code="SPLIMAGE"/>'
            f'<value xsi:type="ED" mediaType="image/jpeg"><reference value="{p.image}"/>'
            "</value></characteristic></subjectOf>"
        )
    return "".join(out)


def _ingredients(p: Product) -> str:
    return "".join(
        f'<ingredient classCode="ACTIB"><quantity><numerator value="{v}" unit="{u}"/>'
        f'<denominator value="1" unit="1"/></quantity><ingredientSubstance>'
        f'<code code="UNII{i}" codeSystem="2.16.840.1.113883.4.9"/><name>{escape(n)}</name>'
        f"</ingredientSubstance></ingredient>"
        for i, (n, v, u) in enumerate(p.ingredients)
    ) + (
        '<ingredient classCode="IACT"><ingredientSubstance><name>MAGNESIUM STEARATE</name>'
        "</ingredientSubstance></ingredient>"
    )


def _marketing(p: Product) -> str:
    high = '<high value="20240101"/>' if p.status == "completed" else ""
    return (
        f'<subjectOf><marketingAct><code code="C53292"/><statusCode code="{p.status}"/>'
        f'<effectiveTime><low value="20100101"/>{high}</effectiveTime></marketingAct></subjectOf>'
    )


def _product(p: Product) -> str:
    dea = (
        f'<subjectOf><policy classCode="DEADrugSchedule"><code code="C48675" '
        f'displayName="{p.dea}"/></policy></subjectOf>'
        if p.dea
        else ""
    )
    parts = "".join(
        f'<part><quantity><numerator value="21" unit="1"/></quantity><partProduct>'
        f"<name>{escape(part.name)}</name>"
        f'<formCode code="C42998" displayName="{part.form}"/>'
        f"<asEntityWithGeneric><genericMedicine><name>{escape(part.generic)}</name>"
        f"</genericMedicine></asEntityWithGeneric>{_ingredients(part)}</partProduct>"
        f"{_marketing(part)}{_characteristics(part)}</part>"
        for part in p.parts
    )
    traits = "" if p.parts else _characteristics(p)
    return (
        "<subject><manufacturedProduct><manufacturedProduct>"
        f'<code code="{p.ndc}" codeSystem="2.16.840.1.113883.6.69"/>'
        f"<name>{escape(p.name)}</name>"
        f'<formCode code="C42931" displayName="{p.form}"/>'
        f"<asEntityWithGeneric><genericMedicine><name>{escape(p.generic)}</name>"
        f"</genericMedicine></asEntityWithGeneric>"
        f"{_ingredients(p) if not p.parts else ''}{parts}"
        f'<asContent><quantity><numerator value="100" unit="1"/></quantity>'
        f'<containerPackagedProduct><code code="{p.ndc}-01" '
        f'codeSystem="2.16.840.1.113883.6.69"/><formCode displayName="BOTTLE"/>'
        f"</containerPackagedProduct></asContent>"
        f"</manufacturedProduct>{_marketing(p)}{dea}{traits}"
        '<consumedIn><substanceAdministration><routeCode displayName="ORAL"/>'
        "</substanceAdministration></consumedIn>"
        "</manufacturedProduct></subject>"
    )


def make_spl(
    products: list[Product],
    *,
    set_id: str | None = None,
    version: int = 1,
    labeler: str = "Acme Pharma, Inc.",
    kind_code: str = "34391-3",
    panel_images: dict[str, str] | None = None,
) -> bytes:
    """An SPL XML document. ``panel_images`` maps image file -> caption text."""
    set_id = set_id or str(uuid.uuid4())
    panels = (
        panel_images
        if panel_images is not None
        else {f"{p.ndc}-label.jpg": f"NDC {p.ndc}-01 {p.name} 100 Tablets" for p in products}
    )
    panel_text = "".join(
        f"<paragraph>{escape(caption)}</paragraph>"
        f'<paragraph><renderMultiMedia referencedObject="IMG{i}"/></paragraph>'
        for i, caption in enumerate(panels.values())
    )
    panel_media = "".join(
        f'<component><observationMedia ID="IMG{i}"><text>image description</text>'
        f'<value xsi:type="ED" mediaType="image/jpeg"><reference value="{file}"/></value>'
        f"</observationMedia></component>"
        for i, file in enumerate(panels)
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="urn:hl7-org:v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <id root="{uuid.uuid4()}"/>
  <code code="{kind_code}" codeSystem="2.16.840.1.113883.6.1"/>
  <title>{escape(products[0].name if products else "Label")} Tablets<br/>Rx only</title>
  <effectiveTime value="20260105"/>
  <setId root="{set_id}"/>
  <versionNumber value="{version}"/>
  <author><assignedEntity><representedOrganization><name>{escape(labeler)}</name>
  </representedOrganization></assignedEntity></author>
  <component><structuredBody>
    <component><section><code code="48780-1"/>{"".join(_product(p) for p in products)}
    </section></component>
    <component><section><code code="51945-4"/><title>PACKAGE LABEL</title>
      <text>{panel_text}</text>{panel_media}
    </section></component>
  </structuredBody></component>
</document>
"""
    return xml.encode()


def make_daily_zip(
    documents: dict[str, bytes],
    *,
    folder: str = "prescription",
    deleted: list[str] | None = None,
    extra_folders: dict[str, dict[str, bytes]] | None = None,
) -> bytes:
    """A DailyMed-style update zip. ``documents`` maps set id -> SPL XML."""

    def label_zip(xml: bytes) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(f"{uuid.uuid4()}.xml", xml)
            z.writestr("label.jpg", b"\xff\xd8\xff")
        return buf.getvalue()

    buf = io.BytesIO()
    added: list[str] = []
    with zipfile.ZipFile(buf, "w") as z:
        for name, docs in {folder: documents, **(extra_folders or {})}.items():
            for set_id, xml in docs.items():
                entry = f"{name}/20261111_{set_id}.zip"
                added.append(entry)
                z.writestr(entry, label_zip(xml))
        z.writestr("files_added.txt", "\n".join(added))
        z.writestr(
            "files_deleted.txt",
            "\n".join(f"prescription/20200101_{s}.zip" for s in deleted or []),
        )
    return buf.getvalue()
