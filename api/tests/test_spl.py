from __future__ import annotations

from datetime import date

import pytest

from pillmark.spl import SPLParseError, parse_spl

from .spl_factory import Product, make_spl


def test_parses_document_metadata() -> None:
    xml = make_spl([Product()], set_id="AC018F64-FD9D-4B3C-B0AC-CA305B8DF635", version=4)
    label = parse_spl(xml)
    assert label.set_id == "ac018f64-fd9d-4b3c-b0ac-ca305b8df635"
    assert label.version == 4
    assert label.effective_date == date(2026, 1, 5)
    assert label.labeler == "Acme Pharma, Inc."
    assert label.kind == "rx"
    assert label.title == "Testamol Tablets Rx only"


def test_parses_pill_characteristics() -> None:
    label = parse_spl(make_spl([Product(dea="CII")]))
    [pill] = label.pills
    assert pill.product_code == "0000-0001"
    assert pill.part == 0
    assert pill.name == "Testamol"
    assert pill.generic_name == "testamol hydrochloride"
    assert pill.dosage_form == "TABLET, FILM COATED"
    assert pill.route == "ORAL"
    assert pill.strength == "500 mg"
    assert [i.name for i in pill.ingredients] == ["TESTAMOL HYDROCHLORIDE"]
    assert pill.imprint.display == "TM 500"
    assert pill.imprint.key == "TM500"
    assert pill.colors == ("white",)
    assert pill.shape == "oval"
    assert pill.size_mm == 17
    assert pill.score == 2
    assert pill.dea_schedule == "CII"
    assert pill.marketed is True
    assert pill.marketing_start == date(2010, 1, 1)
    assert pill.packages == ["0000-0001-01"]


def test_two_tone_capsule_keeps_both_colors_in_order() -> None:
    product = Product(form="CAPSULE", colors=["blue", "white"], shape="capsule", score=1)
    [pill] = parse_spl(make_spl([product])).pills
    assert pill.colors == ("blue", "white")


def test_implausible_sizes_are_dropped() -> None:
    capsule = Product(form="CAPSULE", shape="capsule", size=2)  # a capsule size number
    tablet = Product(ndc="0000-0002", size=3)
    pills = parse_spl(make_spl([capsule, tablet])).pills
    assert [p.size_mm for p in pills] == [None, 3]


def test_combination_strength() -> None:
    product = Product(ingredients=[("A", "5", "mg"), ("B", "325", "mg")])
    [pill] = parse_spl(make_spl([product])).pills
    assert pill.strength == "5 mg / 325 mg"


def test_discontinued_product_is_kept_but_flagged() -> None:
    [pill] = parse_spl(make_spl([Product(status="completed")])).pills
    assert pill.marketed is False
    assert pill.marketing_end == date(2024, 1, 1)


def test_non_solid_products_are_skipped() -> None:
    syrup = Product(ndc="0000-0002", form="SOLUTION", imprint=None, shape=None, colors=[])
    label = parse_spl(make_spl([Product(), syrup]))
    assert [p.product_code for p in label.pills] == ["0000-0001"]


def test_label_photos_are_matched_by_ndc() -> None:
    products = [Product(ndc="0000-0001"), Product(ndc="0000-0002", imprint="TM;250")]
    panels = {
        "two.jpg": "NDC 0000-0002-01 Testamol 250 mg",
        "one.jpg": "NDC 00000-0001-01 Testamol 500 mg",  # 11-digit padded form
    }
    label = parse_spl(make_spl(products, panel_images=panels))
    by_code = {p.product_code: p.label_image for p in label.pills}
    assert by_code == {"0000-0001": "one.jpg", "0000-0002": "two.jpg"}
    assert label.label_images == ["two.jpg", "one.jpg"]


def test_label_photo_falls_back_to_strength_then_first_image() -> None:
    products = [
        Product(ndc="0000-0001", ingredients=[("X", "10", "mg")]),
        Product(ndc="0000-0002", ingredients=[("X", "20", "mg")]),
        Product(ndc="0000-0003", ingredients=[("X", "40", "mg")]),
    ]
    panels = {"a.jpg": "Testamol 10 mg bottle", "b.jpg": "Testamol 20 mg bottle"}
    label = parse_spl(make_spl(products, panel_images=panels))
    assert [p.label_image for p in label.pills] == ["a.jpg", "b.jpg", "a.jpg"]


def test_pill_photo_from_splimage() -> None:
    [pill] = parse_spl(make_spl([Product(image="pill-500.jpg")])).pills
    assert pill.pill_image == "pill-500.jpg"


def test_kit_parts_become_separate_pills() -> None:
    active = Product(name="Activa", colors=["blue"], shape="round", imprint="b;987", size=6)
    inert = Product(
        name="Inert", colors=["white"], shape="round", imprint="b;143", size=6, ingredients=[]
    )
    kit = Product(ndc="1111-222", name="Kit", form="KIT", parts=[active, inert])
    label = parse_spl(make_spl([kit]))
    assert [(p.part, p.name, p.imprint.key, p.colors) for p in label.pills] == [
        (1, "Activa", "B987", ("blue",)),
        (2, "Inert", "B143", ("white",)),
    ]
    assert {p.product_code for p in label.pills} == {"1111-222"}


def test_otc_and_other_kinds() -> None:
    assert parse_spl(make_spl([Product()], kind_code="34390-5")).kind == "otc"
    assert parse_spl(make_spl([Product()], kind_code="99999-9")).kind == "other"


@pytest.mark.parametrize(
    "xml",
    [
        b"not xml",
        b"<root/>",
        b'<document xmlns="urn:hl7-org:v3"><title>no ids</title></document>',
    ],
)
def test_rejects_documents_it_cannot_read(xml: bytes) -> None:
    with pytest.raises(SPLParseError):
        parse_spl(xml)


def test_does_not_resolve_external_entities() -> None:
    xml = b"""<?xml version="1.0"?>
<!DOCTYPE document [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<document xmlns="urn:hl7-org:v3"><id root="00000000-0000-0000-0000-000000000001"/>
<setId root="00000000-0000-0000-0000-000000000002"/><title>&xxe;</title></document>"""
    label = parse_spl(xml)
    assert "root:" not in (label.title or "")
