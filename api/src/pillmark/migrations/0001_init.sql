-- Pillmark schema, version 1.
--
-- labels: one row per DailyMed SPL set id (the latest version we have seen).
-- pills:  one row per solid oral product (or kit part) in a label.
--
-- Needs PostgreSQL 15 or newer (UNIQUE NULLS NOT DISTINCT).

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

CREATE TABLE labels (
    set_id          uuid PRIMARY KEY,
    document_id     uuid        NOT NULL,
    version         integer     NOT NULL,
    effective_date  date,
    title           text,
    labeler         text,
    kind            text        NOT NULL DEFAULT 'other',
    label_images    text[]      NOT NULL DEFAULT '{}',
    source          text,
    imported_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX labels_labeler_trgm ON labels USING gin (lower(labeler) gin_trgm_ops);

CREATE TABLE pills (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    set_id           uuid    NOT NULL REFERENCES labels (set_id) ON DELETE CASCADE,
    product_code     text,
    part             integer NOT NULL DEFAULT 0,
    name             text,
    generic_name     text,
    dosage_form      text,
    route            text,
    strength         text,
    ingredients      jsonb   NOT NULL DEFAULT '[]',
    imprint_raw      text    NOT NULL DEFAULT '',
    imprint          text    NOT NULL DEFAULT '',
    imprint_sides    text[]  NOT NULL DEFAULT '{}',
    imprint_tokens   text[]  NOT NULL DEFAULT '{}',
    imprint_key      text    NOT NULL DEFAULT '',
    imprint_fold     text    NOT NULL DEFAULT '',
    colors           text[]  NOT NULL DEFAULT '{}',
    shape            text,
    size_mm          real,
    score            smallint,
    has_symbol       boolean NOT NULL DEFAULT false,
    pill_image       text,
    label_image      text,
    dea_schedule     text,
    marketed         boolean NOT NULL DEFAULT true,
    marketing_start  date,
    marketing_end    date,
    packages         text[]  NOT NULL DEFAULT '{}',
    -- Same physical pill sold by several labelers (repackagers) shares a fingerprint.
    -- group_size and is_primary are kept up to date by the importer, so searches can
    -- show one row per physical pill without grouping at query time.
    fingerprint      text    NOT NULL,
    group_size       integer NOT NULL DEFAULT 1,
    is_primary       boolean NOT NULL DEFAULT true,
    -- Lower-cased name, generic name and ingredients for "what is it called" search.
    search_text      text    NOT NULL DEFAULT '',
    UNIQUE NULLS NOT DISTINCT (set_id, product_code, part)
);

CREATE INDEX pills_set_id          ON pills (set_id);
CREATE INDEX pills_imprint_key     ON pills (imprint_key);
CREATE INDEX pills_imprint_fold    ON pills (imprint_fold);
CREATE INDEX pills_imprint_trgm    ON pills USING gin (imprint_key gin_trgm_ops);
CREATE INDEX pills_imprint_tokens  ON pills USING gin (imprint_tokens);
CREATE INDEX pills_colors          ON pills USING gin (colors);
CREATE INDEX pills_shape           ON pills (shape);
CREATE INDEX pills_fingerprint     ON pills (fingerprint);
CREATE INDEX pills_primary_shape   ON pills (shape, group_size DESC) WHERE is_primary;
CREATE INDEX pills_search_text     ON pills USING gin (search_text gin_trgm_ops);

CREATE TABLE import_runs (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source           text        NOT NULL,
    status           text        NOT NULL DEFAULT 'running'
                     CHECK (status IN ('running', 'succeeded', 'failed', 'missing')),
    started_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz,
    documents        integer     NOT NULL DEFAULT 0,
    labels_upserted  integer     NOT NULL DEFAULT 0,
    labels_skipped   integer     NOT NULL DEFAULT 0,
    labels_deleted   integer     NOT NULL DEFAULT 0,
    pills_written    integer     NOT NULL DEFAULT 0,
    errors           integer     NOT NULL DEFAULT 0,
    message          text
);

CREATE INDEX import_runs_source ON import_runs (source, status);
