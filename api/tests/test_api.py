from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from pillmark import __version__
from pillmark.api.app import create_app
from pillmark.settings import Settings
from pillmark.spl import parse_spl
from pillmark.store import write_label

from .spl_factory import Product, make_spl

pytestmark = pytest.mark.db

SET_MAKER = "aaaaaaaa-0000-0000-0000-000000000001"
SET_REPACK = "aaaaaaaa-0000-0000-0000-000000000002"
SET_OTHER = "aaaaaaaa-0000-0000-0000-000000000003"


@pytest.fixture
def client(clean_db: str) -> Iterator[TestClient]:
    labels = [
        make_spl(
            [
                Product(
                    ndc="1000-0001",
                    name="Hydrocodone and APAP",
                    generic="hydrocodone and acetaminophen",
                    imprint="M;367",
                    colors=["white"],
                    shape="capsule",
                    size=16,
                    ingredients=[("HYDROCODONE", "10", "mg"), ("ACETAMINOPHEN", "325", "mg")],
                    dea="CII",
                ),
                Product(
                    ndc="1000-0002",
                    name="Lisinopril",
                    generic="lisinopril",
                    imprint="IP;204",
                    colors=["pink"],
                    shape="round",
                    size=7,
                    score=1,
                    ingredients=[("LISINOPRIL", "10", "mg")],
                ),
            ],
            set_id=SET_MAKER,
            labeler="Maker Labs",
        ),
        make_spl(
            [
                Product(
                    ndc="2000-0001",
                    name="Hydrocodone and APAP",
                    generic="hydrocodone and acetaminophen",
                    imprint="M;367",
                    colors=["white"],
                    shape="capsule",
                    size=16,
                    ingredients=[("HYDROCODONE", "10", "mg"), ("ACETAMINOPHEN", "325", "mg")],
                    image="m367.jpg",
                )
            ],
            set_id=SET_REPACK,
            labeler="Repack Co",
        ),
        make_spl(
            [
                Product(
                    ndc="3000-0001",
                    name="Amoxicillin",
                    generic="amoxicillin",
                    form="CAPSULE",
                    imprint="TEVA;3109",
                    colors=["blue", "yellow"],
                    shape="capsule",
                    size=19,
                    score=1,
                    ingredients=[("AMOXICILLIN", "500", "mg")],
                ),
                Product(
                    ndc="3000-0002",
                    name="Plain Aspirin",
                    generic="aspirin",
                    imprint=None,
                    colors=["white"],
                    shape="round",
                    size=8,
                    score=1,
                    ingredients=[("ASPIRIN", "81", "mg")],
                    status="completed",
                ),
                Product(
                    ndc="3000-0003",
                    name="Testolol",
                    generic="testolol",
                    imprint="M;357",
                    colors=["white"],
                    shape="round",
                    size=8,
                    ingredients=[("TESTOLOL", "5", "mg")],
                ),
            ],
            set_id=SET_OTHER,
            labeler="Other Pharma",
        ),
    ]
    with psycopg.connect(clean_db) as conn:
        for xml in labels:
            write_label(conn, parse_spl(xml), source="test")
        conn.commit()
    settings = Settings(DATABASE_URL=clean_db, build="42", commit="abc123")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def search(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get("/v1/pills", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_health_and_meta(client: TestClient) -> None:
    health = client.get("/v1/health")
    assert health.json() == {
        "status": "ok",
        "database": "ok",
        "version": __version__,
        "build": "42",
    }
    assert health.headers["X-Pillmark-Version"] == f"{__version__}+42"
    meta = client.get("/v1/meta").json()
    assert meta["commit"] == "abc123"
    assert meta["dataset"]["labels"] == 3
    assert meta["dataset"]["pills"] == 6
    assert meta["dataset"]["with_imprint"] == 5
    assert "Poison Control" in meta["disclaimer"]


def test_vocab(client: TestClient) -> None:
    body = client.get("/v1/vocab").json()
    assert body["colors"][0] == {
        "key": "white",
        "label": "White",
        "nci_code": "C48325",
        "hex": "#F6F4EE",
    }
    assert {s["key"] for s in body["shapes"]} >= {"round", "capsule", "oval"}


@pytest.mark.parametrize("typed", ["M 367", "m367", "367 M", "M-367"])
def test_imprint_matches_however_it_is_typed(client: TestClient, typed: str) -> None:
    body = search(client, imprint=typed)
    first = body["results"][0]
    assert first["imprint"] == "M 367"
    assert first["match_score"] >= 0.97


def test_repackagers_are_grouped(client: TestClient) -> None:
    body = search(client, imprint="M367")
    [first, *rest] = body["results"]
    assert first["group_size"] == 2
    # The listing with a pill photo represents the group.
    assert first["labeler"] == "Repack Co"
    assert first["photo_url"].endswith("name=m367.jpg")
    assert first["label_image_url"].startswith("https://dailymed.nlm.nih.gov/dailymed/image.cfm")
    assert [r["imprint"] for r in rest] == ["M 357"]  # one character off, ranked lower
    assert rest[0]["match_score"] < 0.7

    ungrouped = search(client, imprint="M367", group="false")
    assert [r["imprint"] for r in ungrouped["results"]][:2] == ["M 367", "M 367"]


def test_look_alike_characters(client: TestClient) -> None:
    assert search(client, imprint="1P 2O4")["results"][0]["imprint"] == "IP 204"


def test_filters(client: TestClient) -> None:
    round_white = search(client, color="white", shape="round")
    assert {r["name"] for r in round_white["results"]} == {"Plain Aspirin", "Testolol"}
    two_tone = search(client, color=["blue", "yellow"])
    assert [r["name"] for r in two_tone["results"]] == ["Amoxicillin"]
    assert search(client, color="blue,yellow")["total"] == 1
    assert search(client, shape="Capsule / oblong", size=19)["results"][0]["name"] == "Amoxicillin"
    assert search(client, size=7, size_tolerance=0)["results"][0]["name"] == "Lisinopril"
    assert {r["name"] for r in search(client, has_imprint="false")["results"]} == {"Plain Aspirin"}
    assert search(client, color="white", shape="round", include_discontinued="false")["total"] == 1


def test_name_search(client: TestClient) -> None:
    body = search(client, q="lisinopril")
    assert [r["name"] for r in body["results"]] == ["Lisinopril"]
    assert search(client, q="other pharma")["total"] == 3
    # Every word must appear somewhere: name, generic name, ingredient or labeler.
    assert [r["name"] for r in search(client, q="lisinopril maker")["results"]] == ["Lisinopril"]


def test_name_search_matches_any_labeler_in_a_group(client: TestClient) -> None:
    [result] = search(client, q="maker labs", imprint="M367")["results"]
    assert result["group_size"] == 2


def test_name_search_tolerates_typos(client: TestClient) -> None:
    body = search(client, q="lisinoprl")
    assert body["results"][0]["name"] == "Lisinopril"
    assert body["results"][0]["match_score"] < 1


def test_pagination(client: TestClient) -> None:
    page = search(client, color="white", limit=1, offset=1)
    assert page["total"] == 3
    assert len(page["results"]) == 1
    assert (page["limit"], page["offset"]) == (1, 1)


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "at least one"),
        ({"imprint": ";;;"}, "at least one"),
        ({"color": "mauve"}, "Unknown color"),
        ({"shape": "blob"}, "Unknown shape"),
    ],
)
def test_validation(client: TestClient, params: dict[str, str], message: str) -> None:
    response = client.get("/v1/pills", params=params)
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_pill_detail_similar_and_label(client: TestClient) -> None:
    pill_id = search(client, imprint="M367", group="false")["results"][1]["id"]
    detail = client.get(f"/v1/pills/{pill_id}").json()
    assert detail["dea_schedule"] in {"CII", None}
    assert [i["name"] for i in detail["ingredients"]] == ["HYDROCODONE", "ACETAMINOPHEN"]
    assert detail["strength"] == "10 mg / 325 mg"
    assert detail["label"]["dailymed_url"].endswith(f"setid={detail['set_id']}")
    assert detail["group_size"] == 2

    similar = client.get(f"/v1/pills/{pill_id}/similar").json()
    assert len(similar["results"]) == 1
    assert similar["results"][0]["id"] != pill_id

    label = client.get(f"/v1/labels/{SET_OTHER}").json()
    assert label["label"]["labeler"] == "Other Pharma"
    assert len(label["pills"]) == 3


def test_not_found(client: TestClient) -> None:
    assert client.get("/v1/pills/999999").status_code == 404
    assert client.get("/v1/labels/aaaaaaaa-0000-0000-0000-00000000ffff").status_code == 404
    assert client.get("/v1/labels/not-a-uuid").status_code == 422


def test_cors_and_cache_headers(client: TestClient) -> None:
    response = client.get(
        "/v1/pills", params={"imprint": "IP204"}, headers={"Origin": "https://example.org"}
    )
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers["cache-control"] == "public, max-age=300"


def test_openapi_lists_the_public_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) >= {
        "/v1/pills",
        "/v1/pills/{pill_id}",
        "/v1/pills/{pill_id}/similar",
        "/v1/labels/{set_id}",
        "/v1/vocab",
        "/v1/meta",
        "/v1/health",
    }
