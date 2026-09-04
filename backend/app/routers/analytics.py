from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db)):
    total_signals = db.execute(text("SELECT count(*) FROM risk_signals WHERE is_active")).scalar()
    total_reports = db.execute(text("SELECT count(*) FROM crowd_reports")).scalar()
    total_damage = db.execute(
        text("SELECT count(*) FROM risk_signals WHERE type = 'road_damage' AND is_active")
    ).scalar()
    total_blackspots = db.execute(
        text("SELECT count(*) FROM risk_signals WHERE type = 'accident_blackspot' AND is_active")
    ).scalar()
    total_queries = db.execute(text("SELECT count(*) FROM route_queries")).scalar()

    by_type_rows = db.execute(
        text("SELECT type, count(*) AS c FROM risk_signals WHERE is_active GROUP BY type")
    ).all()
    avg_sev_rows = db.execute(
        text("SELECT type, avg(severity) AS a FROM risk_signals WHERE is_active GROUP BY type")
    ).all()

    return AnalyticsSummary(
        total_risk_signals=total_signals or 0,
        total_crowd_reports=total_reports or 0,
        total_road_damage_detections=total_damage or 0,
        total_accident_blackspots=total_blackspots or 0,
        total_route_queries=total_queries or 0,
        signals_by_type={row.type: row.c for row in by_type_rows},
        avg_severity_by_type={row.type: round(float(row.a), 2) for row in avg_sev_rows},
    )


@router.get("/risk-by-area")
def risk_by_area(db: Session = Depends(get_db), grid_size_deg: float = 0.01):
    """Buckets risk signals into a coarse lat/lng grid so the dashboard can
    show a 'risk hot-spot' heat table without needing a full GIS client."""
    rows = db.execute(
        text("""
            SELECT
                round((ST_Y(geom::geometry) / :g))::int * :g AS lat_bucket,
                round((ST_X(geom::geometry) / :g))::int * :g AS lng_bucket,
                count(*) AS signal_count,
                avg(severity) AS avg_severity
            FROM risk_signals
            WHERE is_active
            GROUP BY lat_bucket, lng_bucket
            ORDER BY signal_count DESC
            LIMIT 50
        """),
        {"g": grid_size_deg},
    ).mappings().all()
    return [dict(r) for r in rows]
