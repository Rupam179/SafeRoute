from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.routers import routes, risk_signals, crowd_reports, analytics, damage_detection


INIT_SQL = [
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    """CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS risk_signals (
        id BIGSERIAL PRIMARY KEY,
        geom GEOGRAPHY(Point, 4326) NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('accident_blackspot','road_damage','crowd_safety_report','crime_stat','poi_density','lighting')),
        severity SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),
        source TEXT NOT NULL,
        meta JSONB DEFAULT '{}'::jsonb,
        time_of_day TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_risk_signals_geom ON risk_signals USING GIST (geom)",
    "CREATE INDEX IF NOT EXISTS idx_risk_signals_type ON risk_signals (type)",
    "CREATE INDEX IF NOT EXISTS idx_risk_signals_active ON risk_signals (is_active)",
    """CREATE TABLE IF NOT EXISTS crowd_reports (
        id BIGSERIAL PRIMARY KEY,
        geom GEOGRAPHY(Point, 4326) NOT NULL,
        reporter_id UUID REFERENCES users(id) ON DELETE SET NULL,
        lighting TEXT CHECK (lighting IN ('good','moderate','poor','unknown')) DEFAULT 'unknown',
        activity_level TEXT CHECK (activity_level IN ('high','medium','low','unknown')) DEFAULT 'unknown',
        incident_report BOOLEAN NOT NULL DEFAULT FALSE,
        notes TEXT,
        reported_at_hour SMALLINT CHECK (reported_at_hour BETWEEN 0 AND 23),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        risk_signal_id BIGINT REFERENCES risk_signals(id) ON DELETE SET NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_crowd_reports_geom ON crowd_reports USING GIST (geom)",
    """CREATE TABLE IF NOT EXISTS route_queries (
        id BIGSERIAL PRIMARY KEY,
        origin GEOGRAPHY(Point, 4326) NOT NULL,
        destination GEOGRAPHY(Point, 4326) NOT NULL,
        origin_label TEXT,
        destination_label TEXT,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        result_summary JSONB
    )""",
    """CREATE TABLE IF NOT EXISTS model_predictions (
        id BIGSERIAL PRIMARY KEY,
        geom GEOGRAPHY(Point, 4326),
        image_ref TEXT,
        model_version TEXT NOT NULL,
        predictions JSONB NOT NULL,
        max_severity SMALLINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        risk_signal_id BIGINT REFERENCES risk_signals(id) ON DELETE SET NULL
    )""",
]


def run_schema():
    """Run schema on startup — safe to run multiple times (IF NOT EXISTS)."""
    with engine.connect() as conn:
        for stmt in INIT_SQL:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
        conn.commit()


run_schema()

app = FastAPI(
    title="SafeRoute API",
    description="AI-powered risk-aware navigation — routing, risk signals, crowd reports, analytics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
app.include_router(risk_signals.router)
app.include_router(crowd_reports.router)
app.include_router(analytics.router)
app.include_router(damage_detection.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "saferoute-backend"}


@app.get("/")
def root():
    return {
        "message": "SafeRoute API",
        "docs": "/docs",
        "endpoints": [
            "POST /api/routes",
            "GET  /api/risk-signals",
            "POST /api/crowd-reports",
            "GET  /api/crowd-reports",
            "GET  /api/analytics/summary",
            "GET  /api/analytics/risk-by-area",
            "POST /api/damage-detection",
        ],
    }
