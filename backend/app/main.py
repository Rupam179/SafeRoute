from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import routes, risk_signals, crowd_reports, analytics, damage_detection

Base.metadata.create_all(bind=engine)

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
