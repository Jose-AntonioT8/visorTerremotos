CREATE TABLE fecha (
    fecha_id date PRIMARY KEY
);

CREATE TABLE pais (
    country_id text PRIMARY KEY,
    name_es text,
    admin_name text,
    continent text,
    subregion text
);

CREATE TABLE evento_actual (
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
    fecha_id date NOT NULL REFERENCES fecha (fecha_id),
    country_id text REFERENCES pais (country_id),
    source text NOT NULL,
    mode text NOT NULL
);

CREATE INDEX evento_actual_occurred_at_idx ON evento_actual (occurred_at);

CREATE TABLE evento_version (
    event_id text NOT NULL,
    updated_ms bigint NOT NULL,
    original jsonb NOT NULL,
    ingested_at timestamptz NOT NULL,
    PRIMARY KEY (event_id, updated_ms)
);

CREATE TABLE cuarentena (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    motivo text NOT NULL,
    original jsonb NOT NULL,
    ingested_at timestamptz NOT NULL
);

CREATE TABLE publicacion (
    event_id text PRIMARY KEY,
    updated_ms bigint NOT NULL,
    published_at timestamptz NOT NULL
);

CREATE TABLE consulta_fuente (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    consulted_at timestamptz NOT NULL,
    url text,
    intervalo text,
    record_count integer,
    resultado text NOT NULL
);
