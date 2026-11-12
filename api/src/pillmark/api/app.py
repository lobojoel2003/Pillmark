"""The Pillmark public API."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from pillmark import __version__
from pillmark.api.schemas import (
    ColorOut,
    DatasetStats,
    HealthResponse,
    LabelResponse,
    LastImport,
    MetaResponse,
    PillDetail,
    SearchEcho,
    SearchResponse,
    ShapeOut,
    SimilarResponse,
    VocabResponse,
    detail_from_row,
    label_from_row,
    summary_from_row,
)
from pillmark.db import migrate
from pillmark.search import MAX_LIMIT, SearchQuery, build_get, build_search, build_similar
from pillmark.settings import Settings, get_settings
from pillmark.vocab import (
    COLORS,
    SHAPES,
    normalize_color_param,
    normalize_shape_param,
)

log = logging.getLogger(__name__)

DESCRIPTION = """
Identify a pill from its **imprint**, **color**, **shape** and **size**.

Data comes from FDA drug labels published by the U.S. National Library of Medicine
on [DailyMed](https://dailymed.nlm.nih.gov) and is refreshed nightly.

The API is free, open and needs no key. Responses are JSON.

> Not medical advice. If someone may have swallowed a pill that is not theirs, call
> Poison Control (US: **1-800-222-1222**) or your local emergency number.
"""

TAGS = [
    {"name": "pills", "description": "Search and look up pills."},
    {"name": "labels", "description": "DailyMed drug labels."},
    {"name": "reference", "description": "Colors, shapes and service information."},
]

Pool = AsyncConnectionPool[AsyncConnection[DictRow]]

SEARCH_CACHE = "public, max-age=300"
STATIC_CACHE = "public, max-age=86400"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    pool: Pool = AsyncConnectionPool(
        settings.database_url,
        connection_class=AsyncConnection[DictRow],
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        kwargs={"row_factory": dict_row, "application_name": "pillmark-api"},
        open=False,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.migrate_on_start:
            applied = migrate(settings.database_url)
            if applied:
                log.info("applied migrations: %s", ", ".join(applied))
        await pool.open(wait=False)
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(
        title="Pillmark API",
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"},
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = settings
    app.state.pool = pool

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
        max_age=86400,
    )

    @app.middleware("http")
    async def version_header(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Pillmark-Version"] = f"{__version__}+{settings.build}"
        return response

    register_routes(app)
    return app


# ------------------------------------------------------------------------ dependencies


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _pool(request: Request) -> Pool:
    pool: Pool = request.app.state.pool
    return pool


SettingsDep = Annotated[Settings, Depends(_settings)]
PoolDep = Annotated[Pool, Depends(_pool)]


async def _fetch_all(pool: Pool, query: Any, params: Any) -> list[dict[str, Any]]:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(query, params)
        rows: list[dict[str, Any]] = await cur.fetchall()
        return rows


async def _fetch_one(pool: Pool, query: Any, params: Any) -> dict[str, Any] | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(query, params)
        row: dict[str, Any] | None = await cur.fetchone()
        return row


def _split(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        out.extend(v.strip() for v in value.split(",") if v.strip())
    return out


# ------------------------------------------------------------------------------ routes


def register_routes(app: FastAPI) -> None:
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "Pillmark API",
            "version": __version__,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/v1/health", response_model=HealthResponse, tags=["reference"])
    async def health(settings: SettingsDep, pool: PoolDep) -> JSONResponse:
        """Liveness and database connectivity."""
        database = "ok"
        try:
            await _fetch_one(pool, "SELECT 1 AS ok", None)
        except Exception as exc:  # report any failure as "down"
            log.warning("health check failed: %s", exc)
            database = "down"
        body = HealthResponse(
            status="ok" if database == "ok" else "degraded",
            database=database,
            version=__version__,
            build=settings.build,
        )
        return JSONResponse(body.model_dump(), status_code=200 if database == "ok" else 503)

    @app.get("/v1/meta", response_model=MetaResponse, tags=["reference"])
    async def meta(settings: SettingsDep, pool: PoolDep, response: Response) -> MetaResponse:
        """Version, build and dataset size."""
        stats = await _fetch_one(
            pool,
            """
            SELECT (SELECT count(*) FROM labels) AS labels,
                   count(*) AS pills,
                   count(*) FILTER (WHERE imprint_key <> '') AS with_imprint,
                   (SELECT count(DISTINCT labeler) FROM labels) AS labelers
            FROM pills
            """,
            None,
        )
        last = await _fetch_one(
            pool,
            """
            SELECT source, status, finished_at, labels_upserted, pills_written
            FROM import_runs WHERE status = 'succeeded'
            ORDER BY finished_at DESC NULLS LAST LIMIT 1
            """,
            None,
        )
        response.headers["Cache-Control"] = SEARCH_CACHE
        return MetaResponse(
            version=__version__,
            build=settings.build,
            commit=settings.commit,
            dataset=DatasetStats(
                **(stats or {"labels": 0, "pills": 0, "with_imprint": 0, "labelers": 0}),
                last_import=LastImport(**last) if last else None,
            ),
        )

    @app.get("/v1/vocab", response_model=VocabResponse, tags=["reference"])
    async def vocab(response: Response) -> VocabResponse:
        """Colors and shapes the search understands, with drawing colors."""
        response.headers["Cache-Control"] = STATIC_CACHE
        return VocabResponse(
            colors=[ColorOut(**c.as_dict()) for c in COLORS],
            shapes=[ShapeOut(**s.as_dict()) for s in SHAPES],
        )

    @app.get("/v1/pills", response_model=SearchResponse, tags=["pills"])
    async def search_pills(
        settings: SettingsDep,
        pool: PoolDep,
        response: Response,
        imprint: Annotated[
            str | None,
            Query(max_length=64, description="Text on the pill, any side, e.g. `M 367`."),
        ] = None,
        color: Annotated[
            list[str],
            Query(description="Color key; repeat or comma-separate for two-tone pills."),
        ] = [],  # noqa: B006 - FastAPI copies defaults per request
        shape: Annotated[str | None, Query(description="Shape key, e.g. `round`.")] = None,
        size: Annotated[
            float | None, Query(ge=1, le=60, description="Longest side in millimetres.")
        ] = None,
        size_tolerance: Annotated[float, Query(ge=0, le=10)] = 1.0,
        score: Annotated[
            int | None, Query(ge=1, le=8, description="Pieces the score lines make.")
        ] = None,
        name: Annotated[
            str | None,
            Query(
                max_length=100,
                alias="q",
                description="Drug, brand, ingredient or labeler name.",
            ),
        ] = None,
        has_imprint: Annotated[
            bool | None, Query(description="Only pills with (true) or without (false) text.")
        ] = None,
        include_discontinued: bool = True,
        group: Annotated[
            bool, Query(description="Collapse repackagers of the same pill into one result.")
        ] = True,
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 24,
        offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    ) -> SearchResponse:
        """Find pills by what they look like. At least one criterion is required."""
        colors: list[str] = []
        for raw in _split(color):
            key = normalize_color_param(raw)
            if key is None:
                raise HTTPException(
                    422, f"Unknown color {raw!r}. Use one of: {', '.join(c.key for c in COLORS)}."
                )
            colors.append(key)
        shape_key = None
        if shape:
            shape_key = normalize_shape_param(shape)
            if shape_key is None:
                raise HTTPException(
                    422, f"Unknown shape {shape!r}. Use one of: {', '.join(s.key for s in SHAPES)}."
                )

        query = SearchQuery(
            imprint=imprint,
            colors=colors,
            shape=shape_key,
            size_mm=size,
            size_tolerance=size_tolerance,
            score=score,
            name=name,
            has_imprint=has_imprint,
            include_discontinued=include_discontinued,
            group=group,
            limit=limit,
            offset=offset,
        )
        if query.is_empty():
            raise HTTPException(
                422, "Give at least one of imprint, color, shape, size, score or q."
            )

        sql_text, params = build_search(query)
        rows = await _fetch_all(pool, sql_text, params)
        if not rows and query.name and query.offset == 0:
            query.fuzzy_name = True  # nothing has every word: allow typos
            sql_text, params = build_search(query)
            rows = await _fetch_all(pool, sql_text, params)
        response.headers["Cache-Control"] = SEARCH_CACHE
        return SearchResponse(
            query=SearchEcho(
                imprint=imprint,
                imprint_key=query.imprint_key or None,
                colors=colors,
                shape=shape_key,
                size_mm=size,
                score=score,
                name=name,
            ),
            total=int(rows[0]["total"]) if rows else 0,
            limit=params["limit"],
            offset=params["offset"],
            results=[summary_from_row(r, settings.dailymed_base) for r in rows],
        )

    @app.get(
        "/v1/pills/{pill_id}",
        response_model=PillDetail,
        tags=["pills"],
        responses={404: {"description": "No pill with that id."}},
    )
    async def get_pill(
        pill_id: int, settings: SettingsDep, pool: PoolDep, response: Response
    ) -> PillDetail:
        """Everything known about one pill, with its label."""
        sql_text, params = build_get(pill_id)
        row = await _fetch_one(pool, sql_text, params)
        if row is None:
            raise HTTPException(404, "Pill not found.")
        response.headers["Cache-Control"] = SEARCH_CACHE
        return detail_from_row(row, settings.dailymed_base)

    @app.get("/v1/pills/{pill_id}/similar", response_model=SimilarResponse, tags=["pills"])
    async def similar_pills(
        pill_id: int, settings: SettingsDep, pool: PoolDep, response: Response
    ) -> SimilarResponse:
        """The same physical pill as sold by other labelers and repackagers."""
        sql_text, params = build_similar(pill_id)
        rows = await _fetch_all(pool, sql_text, params)
        response.headers["Cache-Control"] = SEARCH_CACHE
        return SimilarResponse(
            pill_id=pill_id, results=[summary_from_row(r, settings.dailymed_base) for r in rows]
        )

    @app.get(
        "/v1/labels/{set_id}",
        response_model=LabelResponse,
        tags=["labels"],
        responses={404: {"description": "No label with that set id."}},
    )
    async def get_label(
        set_id: UUID, settings: SettingsDep, pool: PoolDep, response: Response
    ) -> LabelResponse:
        """A DailyMed label and the pills in it."""
        label = await _fetch_one(pool, "SELECT * FROM labels WHERE set_id = %s", (set_id,))
        if label is None:
            raise HTTPException(404, "Label not found.")
        rows = await _fetch_all(
            pool,
            """
            SELECT p.*, l.labeler, l.effective_date, l.version, l.kind, l.title,
                   1.0::real AS match_score
            FROM pills p JOIN labels l ON l.set_id = p.set_id
            WHERE p.set_id = %s ORDER BY p.part, p.product_code, p.id
            """,
            (set_id,),
        )
        response.headers["Cache-Control"] = SEARCH_CACHE
        return LabelResponse(
            label=label_from_row(label, settings.dailymed_base),
            pills=[summary_from_row(r, settings.dailymed_base) for r in rows],
        )


app = create_app()
