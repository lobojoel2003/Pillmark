"""Response models for the public API."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pillmark.sources import image_url

DISCLAIMER = (
    "Pillmark is for information only and is not medical advice. Always confirm a pill "
    "with a pharmacist. If someone may have swallowed a pill that is not theirs, call "
    "Poison Control (US: 1-800-222-1222) or your local emergency number now."
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Ingredient(ApiModel):
    name: str
    strength: str | None = None
    unii: str | None = Field(default=None, description="FDA Unique Ingredient Identifier.")


class PillSummary(ApiModel):
    id: int
    set_id: str = Field(description="DailyMed SPL set id of the label this pill comes from.")
    product_code: str | None = Field(description="NDC product code (labeler-product).")
    name: str | None
    generic_name: str | None
    strength: str | None
    dosage_form: str | None
    imprint: str = Field(description="Imprint with sides separated by spaces.")
    imprint_sides: list[str] = Field(description="Imprint text per side or line.")
    colors: list[str] = Field(description="Color keys; two colors for two-tone pills.")
    shape: str | None
    size_mm: float | None
    score: int | None = Field(description="Pieces the score lines break it into (1 = unscored).")
    has_symbol: bool
    labeler: str | None
    marketed: bool
    dea_schedule: str | None
    photo_url: str | None = Field(description="Photo of the pill itself, when the label has one.")
    label_image_url: str | None = Field(description="Photo of the package label.")
    match_score: float = Field(description="How well this pill matches the query, 0 to 1.")
    group_size: int = Field(
        description="Labelers selling this same pill (repackagers share one result)."
    )


class LabelInfo(ApiModel):
    set_id: str
    document_id: str | None = None
    version: int
    effective_date: date | None
    title: str | None
    labeler: str | None
    kind: str
    dailymed_url: str
    images: list[str]


class PillDetail(PillSummary):
    route: str | None
    ingredients: list[Ingredient]
    packages: list[str] = Field(description="NDC package codes.")
    marketing_start: date | None
    marketing_end: date | None
    label: LabelInfo


class SearchEcho(ApiModel):
    imprint: str | None
    imprint_key: str | None
    colors: list[str]
    shape: str | None
    size_mm: float | None
    score: int | None
    name: str | None


class SearchResponse(ApiModel):
    query: SearchEcho
    total: int = Field(description="Matching results (groups when grouping is on).")
    limit: int
    offset: int
    results: list[PillSummary]
    disclaimer: str = DISCLAIMER


class SimilarResponse(ApiModel):
    pill_id: int
    results: list[PillSummary]


class LabelResponse(ApiModel):
    label: LabelInfo
    pills: list[PillSummary]


class ColorOut(ApiModel):
    key: str
    label: str
    nci_code: str
    hex: str


class ShapeOut(ApiModel):
    key: str
    label: str
    nci_code: str
    description: str


class VocabResponse(ApiModel):
    colors: list[ColorOut]
    shapes: list[ShapeOut]


class LastImport(ApiModel):
    source: str
    status: str
    finished_at: Any
    labels_upserted: int
    pills_written: int


class DatasetStats(ApiModel):
    labels: int
    pills: int
    with_imprint: int
    labelers: int
    last_import: LastImport | None


class MetaResponse(ApiModel):
    name: str = "Pillmark"
    version: str
    build: str
    commit: str
    dataset: DatasetStats | None
    source: str = "U.S. National Library of Medicine, DailyMed (dailymed.nlm.nih.gov)"
    disclaimer: str = DISCLAIMER


class HealthResponse(ApiModel):
    status: str
    database: str
    version: str
    build: str


# --------------------------------------------------------------------------- builders


def summary_from_row(row: dict[str, Any], dailymed_base: str) -> PillSummary:
    set_id = str(row["set_id"])
    return PillSummary(
        id=row["id"],
        set_id=set_id,
        product_code=row["product_code"],
        name=row["name"],
        generic_name=row["generic_name"],
        strength=row["strength"],
        dosage_form=row["dosage_form"],
        imprint=row["imprint"],
        imprint_sides=list(row["imprint_sides"] or []),
        colors=list(row["colors"] or []),
        shape=row["shape"],
        size_mm=row["size_mm"],
        score=row["score"],
        has_symbol=row["has_symbol"],
        labeler=row["labeler"],
        marketed=row["marketed"],
        dea_schedule=row["dea_schedule"],
        photo_url=image_url(dailymed_base, set_id, row["pill_image"]),
        label_image_url=image_url(dailymed_base, set_id, row["label_image"]),
        match_score=round(float(row["match_score"]), 3),
        group_size=int(row["group_size"]),
    )


def label_from_row(row: dict[str, Any], dailymed_base: str) -> LabelInfo:
    set_id = str(row["set_id"])
    return LabelInfo(
        set_id=set_id,
        document_id=str(row["document_id"]) if row.get("document_id") else None,
        version=row["version"],
        effective_date=row["effective_date"],
        title=row["title"],
        labeler=row["labeler"],
        kind=row["kind"],
        dailymed_url=f"{dailymed_base}/drugInfo.cfm?setid={set_id}",
        images=[
            url
            for url in (image_url(dailymed_base, set_id, f) for f in row.get("label_images") or [])
            if url
        ],
    )


def detail_from_row(row: dict[str, Any], dailymed_base: str) -> PillDetail:
    summary = summary_from_row(row, dailymed_base)
    return PillDetail(
        **summary.model_dump(),
        route=row["route"],
        ingredients=[Ingredient(**i) for i in row["ingredients"] or []],
        packages=list(row["packages"] or []),
        marketing_start=row["marketing_start"],
        marketing_end=row["marketing_end"],
        label=label_from_row(row, dailymed_base),
    )
