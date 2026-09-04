from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import routes, risk_signals, crowd_reports, analytics, damage_detection


def run_schema():
    """Run init.sql on startup — safe to run multiple times (IF NOT EXISTS)."""
    sql_path = Path(__file__).resolve().parents[3] / "db" / "init.sql"
    if not sql_path.exists():
        # fallback: just create ORM tables
        Base.metadata.create_all(bind=engine)
        return
    sql = sql_path.read_text()
    with engine.connect() as conn:
        # run each statement separately to avoid issues with multi-statement execution
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass  # IF NOT EXISTS guards handle duplicates
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
