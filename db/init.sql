-- ============================================================================
-- SafeRoute — Database Schema
-- PostgreSQL 15+ with PostGIS 3.x
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- for gen_random_uuid()

-- ----------------------------------------------------------------------------
-- USERS  (auth for crowd reporting / dashboard access)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name       TEXT,
    role            TEXT NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- RISK_SIGNALS  — the generic table from the project plan (Section 3.2)
-- One extensible table for every kind of risk instead of N hardcoded tables.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_signals (
    id          BIGSERIAL PRIMARY KEY,
    geom        GEOGRAPHY(Point, 4326) NOT NULL,       -- lat/lng as geography for accurate distance math
    type        TEXT NOT NULL CHECK (
                    type IN (
                        'accident_blackspot',
                        'road_damage',
                        'crowd_safety_report',
                        'crime_stat',
                        'poi_density',
                        'lighting'
                    )
                ),
    severity    SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),  -- 1 = low, 5 = severe
    source      TEXT NOT NULL,               -- e.g. 'MoRTH', 'NCRB', 'crowd', 'yolov8_v1'
    meta        JSONB DEFAULT '{}'::jsonb,   -- free-form: {"damage_class": "pothole", "confidence": 0.91, ...}
    time_of_day TEXT,                        -- 'day' | 'night' | 'any' — used for time-weighting
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

-- Spatial index — this is what makes "find risk near this route" fast
CREATE INDEX IF NOT EXISTS idx_risk_signals_geom ON risk_signals USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_risk_signals_type ON risk_signals (type);
CREATE INDEX IF NOT EXISTS idx_risk_signals_active ON risk_signals (is_active);

-- ----------------------------------------------------------------------------
-- CROWD_REPORTS — raw user submissions (a specialised view feeding risk_signals)
-- Kept separate from risk_signals so we retain the original free-text report,
-- while a trigger/service promotes it into a risk_signal row for scoring.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crowd_reports (
    id              BIGSERIAL PRIMARY KEY,
    geom            GEOGRAPHY(Point, 4326) NOT NULL,
    reporter_id     UUID REFERENCES users(id) ON DELETE SET NULL,  -- nullable = anonymous
    lighting        TEXT CHECK (lighting IN ('good','moderate','poor','unknown')) DEFAULT 'unknown',
    activity_level  TEXT CHECK (activity_level IN ('high','medium','low','unknown')) DEFAULT 'unknown',
    incident_report BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    reported_at_hour SMALLINT CHECK (reported_at_hour BETWEEN 0 AND 23),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    risk_signal_id  BIGINT REFERENCES risk_signals(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_crowd_reports_geom ON crowd_reports USING GIST (geom);

-- ----------------------------------------------------------------------------
-- ROUTE_QUERIES — every routing request, logged for analytics + evaluation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS route_queries (
    id              BIGSERIAL PRIMARY KEY,
    origin          GEOGRAPHY(Point, 4326) NOT NULL,
    destination     GEOGRAPHY(Point, 4326) NOT NULL,
    origin_label    TEXT,
    destination_label TEXT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    result_summary  JSONB   -- cached {fastest: {...}, balanced: {...}, safest: {...}}
);

-- ----------------------------------------------------------------------------
-- MODEL_PREDICTIONS — audit trail of every AI damage-detection call
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_predictions (
    id              BIGSERIAL PRIMARY KEY,
    geom            GEOGRAPHY(Point, 4326),
    image_ref       TEXT,                 -- filename / storage key
    model_version   TEXT NOT NULL,
    predictions     JSONB NOT NULL,       -- raw YOLO output: boxes, classes, confidences
    max_severity    SMALLINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    risk_signal_id  BIGINT REFERENCES risk_signals(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Convenience view: everything currently contributing to risk, with lat/lng
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_risk_signals AS
SELECT
    id,
    ST_Y(geom::geometry) AS lat,
    ST_X(geom::geometry) AS lng,
    type,
    severity,
    source,
    meta,
    time_of_day,
    created_at
FROM risk_signals
WHERE is_active = TRUE;
