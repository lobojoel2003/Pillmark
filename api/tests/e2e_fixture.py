"""Write a small DailyMed-style update zip for end-to-end tests and demos.

python -m tests.e2e_fixture e2e.zip
pillmark import file e2e.zip
"""

from __future__ import annotations

import sys
from pathlib import Path

from .spl_factory import Product, make_daily_zip, make_spl

LABELS: dict[str, tuple[str, list[Product]]] = {
    "e2e00000-0000-4000-8000-000000000001": (
        "Lupin Pharmaceuticals, Inc.",
        [
            Product(
                ndc="68180-513",
                name="Lisinopril",
                generic="lisinopril",
                form="TABLET",
                ingredients=[("LISINOPRIL", "10", "mg")],
                imprint="LUPIN;10",
                colors=["pink"],
                shape="round",
                size=8,
                score=1,
            ),
            Product(
                ndc="68180-514",
                name="Lisinopril",
                generic="lisinopril",
                form="TABLET",
                ingredients=[("LISINOPRIL", "20", "mg")],
                imprint="LUPIN;20",
                colors=["pink"],
                shape="round",
                size=8,
                score=1,
            ),
        ],
    ),
    "e2e00000-0000-4000-8000-000000000002": (
        "Mallinckrodt, Inc.",
        [
            Product(
                ndc="0406-0367",
                name="Hydrocodone Bitartrate and Acetaminophen",
                generic="hydrocodone bitartrate and acetaminophen",
                form="TABLET",
                ingredients=[
                    ("HYDROCODONE BITARTRATE", "10", "mg"),
                    ("ACETAMINOPHEN", "325", "mg"),
                ],
                imprint="M;367",
                colors=["white"],
                shape="capsule",
                size=16,
                score=2,
                dea="CII",
            )
        ],
    ),
    "e2e00000-0000-4000-8000-000000000003": (
        "Bryant Ranch Prepack",
        [
            Product(
                ndc="63629-1234",
                name="Hydrocodone Bitartrate and Acetaminophen",
                generic="hydrocodone bitartrate and acetaminophen",
                form="TABLET",
                ingredients=[
                    ("HYDROCODONE BITARTRATE", "10", "mg"),
                    ("ACETAMINOPHEN", "325", "mg"),
                ],
                imprint="M;367",
                colors=["white"],
                shape="capsule",
                size=16,
                score=2,
                dea="CII",
            )
        ],
    ),
    "e2e00000-0000-4000-8000-000000000004": (
        "Teva Pharmaceuticals USA, Inc.",
        [
            Product(
                ndc="0093-3109",
                name="Amoxicillin",
                generic="amoxicillin",
                form="CAPSULE",
                ingredients=[("AMOXICILLIN", "500", "mg")],
                imprint="TEVA;3109",
                colors=["blue", "yellow"],
                shape="capsule",
                size=19,
                score=1,
            ),
            Product(
                ndc="0093-3107",
                name="Amoxicillin",
                generic="amoxicillin",
                form="CAPSULE",
                ingredients=[("AMOXICILLIN", "250", "mg")],
                imprint="TEVA;3107",
                colors=["blue", "pink"],
                shape="capsule",
                size=16,
                score=1,
                status="completed",
            ),
        ],
    ),
    "e2e00000-0000-4000-8000-000000000005": (
        "Perrigo",
        [
            Product(
                ndc="45802-498",
                name="Ibuprofen",
                generic="ibuprofen",
                form="TABLET, FILM COATED",
                ingredients=[("IBUPROFEN", "200", "mg")],
                imprint="IP;190",
                colors=["orange"],
                shape="oval",
                size=13,
                score=1,
            ),
            Product(
                ndc="45802-499",
                name="Aspirin",
                generic="aspirin",
                form="TABLET",
                ingredients=[("ASPIRIN", "81", "mg")],
                imprint=None,
                colors=["yellow"],
                shape="round",
                size=7,
                score=1,
            ),
        ],
    ),
}


def build() -> bytes:
    documents = {
        set_id: make_spl(products, set_id=set_id, labeler=labeler)
        for set_id, (labeler, products) in LABELS.items()
    }
    return make_daily_zip(documents)


def main(argv: list[str]) -> int:
    target = Path(argv[1] if len(argv) > 1 else "e2e-fixture.zip")
    target.write_bytes(build())
    print(f"wrote {target} ({len(LABELS)} labels)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
