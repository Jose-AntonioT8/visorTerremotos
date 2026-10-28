CREATE SCHEMA IF NOT EXISTS replay;

CREATE TABLE IF NOT EXISTS replay.fecha (
    fecha_id date PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS replay.evento_actual (
    event_id text PRIMARY KEY,
    mag double precision,
    mag_type text,
    place text,
    depth_km double precision,
    lon double precision NOT NULL,
    lat double precision NOT NULL,
    time_ms bigint NOT NULL,
    updated_ms bigint NOT NULL,
    occurred_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    reproduced_at timestamptz,
    fecha_id date NOT NULL REFERENCES replay.fecha (fecha_id),
    country_id text REFERENCES public.pais (country_id),
    source text NOT NULL,
    mode text NOT NULL
);

CREATE INDEX IF NOT EXISTS replay_evento_actual_occurred_at_idx ON replay.evento_actual (occurred_at);

CREATE TABLE IF NOT EXISTS replay.evento_version (
    event_id text NOT NULL,
    updated_ms bigint NOT NULL,
    original jsonb NOT NULL,
    ingested_at timestamptz NOT NULL,
    PRIMARY KEY (event_id, updated_ms)
);

CREATE TABLE IF NOT EXISTS replay.cuarentena (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    motivo text NOT NULL,
    original jsonb NOT NULL,
    ingested_at timestamptz NOT NULL
);
